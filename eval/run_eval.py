"""Evaluation runner: asks the questions in eval/questions.jsonl through the external .NET API and
compares what comes back with the expectations.

Every question is sent to POST /api/ask of the running stack, as a client would send it, with a
request timeout. Whatever comes back, errors and timeouts included, is recorded as the real output.
Results go to eval/results/<run_id>/:
  actual.jsonl  one HTTP exchange per question, as received
  checks.json   run metadata, each question's automatic checks and their counts
  report.md     expected vs actual, for review

The automatic checks compare statuses, section IDs, version decisions and quotes (against the cited
section of the corpus), plus a few regular expressions over the claim texts. They do not measure
semantic correctness; each question's human review starts as "pending".

Standard library only, so it needs no environment of its own; the service never imports it.
Run from the repository root while the stack is up:
    python3 eval/run_eval.py --mode evidence_only
    python3 eval/run_eval.py --mode generative     # paid: one model call per question
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVAL_DIR.parent
DEFAULT_QUESTIONS = EVAL_DIR / "questions.jsonl"
RESULTS_DIR = EVAL_DIR / "results"
KNOWLEDGE_DIR = REPO_ROOT / "data" / "knowledge"
DEFAULT_API = "http://127.0.0.1:8080"

# Longer than the API's own upstream timeout (45 s), so that a slow answer is recorded as the
# API's 504 rather than as a client-side timeout.
REQUEST_TIMEOUT_SECONDS = 60
READINESS_TIMEOUT_SECONDS = 10
# The files that decide a run's result. "dirty" means one of them differs from the commit.
RUN_INPUTS = ("src", "data", "compose.yaml", "eval/questions.jsonl", "eval/run_eval.py")

CHECK_LABELS = {
    "http": "HTTP 200 ve istekle aynı request_id",
    "status": "Beklenen iş durumu",
    "retrieval": "Beklenen bölümlerin tamamı ilk k sonuçta (`retrieved_chunk_ids`)",
    "citation": "Beklenen bölümlerin tamamı kaynak gösterildi (`sources`)",
    "version": "Doğru sürüm kararı (`version_decisions`)",
    "source_validity": (
        "Kaynak/aday geçerli: bölüm korpusta var, alıntı o bölümün birebir metni, belge/sürüm "
        "bilgisi bölüm kaydıyla aynı, getirilen bölüm, seçili sürüm, claim atıfları = `sources` "
        "(kaynak/aday yoksa uygulanmaz)"
    ),
    "no_unnecessary_refusal": "Cevaplanabilir soruda `insufficient_evidence` dönmedi (üretken mod)",
    "no_claims_when_unanswerable": (
        "Cevapsız soruda claim üretilmedi (üretken mod; claim'in anlamsal yanlışlığını ölçmez)"
    ),
    "required_facts": "Gerekli bilgi kalıpları claim'lerde var (sınırlı; anlamsal değil)",
    "forbidden_facts": "Yasak bilgi kalıpları claim'lerde yok (sınırlı; anlamsal değil)",
}
CHECK_NAMES = tuple(CHECK_LABELS)
AS_OF_NOTE = (
    "İsteklerdeki as_of değerlendirilen iş tarihidir (E16 dışında 2026-10-04, E16'da "
    "2026-06-01); gerçek çalıştırma zamanıyla aynı kavram değildir."
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mode", required=True, choices=("evidence_only", "generative"))
    parser.add_argument("--api", default=DEFAULT_API, help=f"default {DEFAULT_API}")
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    args = parser.parse_args(argv)

    questions = load_questions(args.questions)
    sections = load_sections(KNOWLEDGE_DIR)
    api = args.api.rstrip("/")
    readiness = get_json(f"{api}/health/ready", READINESS_TIMEOUT_SECONDS)
    ready = readiness["response"] or {}
    if readiness["http_status"] != 200 or ready.get("status") != "ready":
        print(f"not run: the API is not ready ({describe_failure(readiness)})", file=sys.stderr)
        return 2
    if args.mode == "generative" and not ready["run_metadata"]["generation_configured"]:
        print("blocked: generation is not configured; no model call was made", file=sys.stderr)
        return 2

    git = git_state()
    started = datetime.now().astimezone()
    run_id = f"{started:%Y%m%d-%H%M%S}-{args.mode}"
    exchanges = []
    for question in questions:
        request_id = f"eval.{run_id}.{question['id']}"
        body = {**question["request"], "mode": args.mode}
        exchange = post_json(f"{api}/api/ask", body, request_id, REQUEST_TIMEOUT_SECONDS)
        exchanges.append({"id": question["id"], "request": body, **exchange})
        print(f"{question['id']}: {actual_status(exchange)} ({exchange['elapsed_ms']} ms)")
    finished = datetime.now().astimezone()
    readiness_after = get_json(f"{api}/health/ready", READINESS_TIMEOUT_SECONDS)

    # The raw exchanges are written before anything is computed from them: a paid run is never
    # repeated, so a fault in the checks below must not lose its output.
    out_dir = RESULTS_DIR / run_id
    out_dir.mkdir(parents=True)
    (out_dir / "actual.jsonl").write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in exchanges),
        encoding="utf-8",
    )
    metadata = {
        "run_id": run_id,
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": finished.isoformat(timespec="seconds"),
        "mode": args.mode,
        "api": api,
        "request_timeout_seconds": REQUEST_TIMEOUT_SECONDS,
        "question_count": len(questions),
        # Identifies the question set: a reworded question or rubric changes this hash.
        "questions_sha256": hashlib.sha256(args.questions.read_bytes()).hexdigest(),
        "git": git,
        # Corpus fingerprint, embedding model/revision, LLM model, prompt version/hash, top_k
        # and threshold of the running stack, read before the first question.
        "readiness": ready["run_metadata"],
        "readiness_unchanged": readiness_after["response"] == readiness["response"],
        "as_of_note": AS_OF_NOTE,
    }
    checked = [
        check_question(question, exchange, args.mode, sections)
        for question, exchange in zip(questions, exchanges, strict=True)
    ]
    multi_source = [
        item
        for question, item in zip(questions, checked, strict=True)
        if len(question["expected_source_ids"]) > 1
    ]
    summary = summarize(checked)
    multi_summary = summarize(multi_source)
    checks = {
        "metadata": metadata,
        "summary": summary,
        "multi_source_summary": {name: multi_summary[name] for name in ("retrieval", "citation")},
        "questions": checked,
    }
    (out_dir / "checks.json").write_text(
        json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "report.md").write_text(
        render_report(metadata, questions, exchanges, checked, summary, multi_summary),
        encoding="utf-8",
    )
    for name in CHECK_NAMES:
        counts = summary[name]
        print(f"{name}: {counts['passed']}/{counts['applicable']}")
    print(f"written: {out_dir}")
    return 0


def load_questions(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


FRONTMATTER_FIELD = re.compile(r"^(doc_id|title|version|valid_from|valid_to): *(.*)$")
SECTION_HEADING = re.compile(r"^## (?P<heading>\S.*?) \{#(?P<section_id>[^{}]+)\}$")


def load_sections(knowledge_dir: Path) -> dict[str, dict]:
    """Every corpus section by chunk_id, read independently of the service's loader."""
    sections = {}
    for path in sorted(knowledge_dir.glob("*.md")):
        sections.update(parse_document(path.read_text(encoding="utf-8")))
    return sections


def parse_document(text: str) -> dict[str, dict]:
    """One corpus file in the supported format (front matter, then "## Heading {#id}" sections)
    as source records shaped like the API's source objects: the quote is the section's text
    between its heading and the next one, without surrounding whitespace."""
    _, front, body = text.split("---\n", 2)
    meta = {}
    for line in front.splitlines():
        match = FRONTMATTER_FIELD.match(line)
        if match:
            value = match.group(2).strip().strip('"')
            meta[match.group(1)] = None if value == "null" else value
    sections, current = {}, None
    for line in body.splitlines():
        heading = SECTION_HEADING.match(line)
        if heading:
            current = {
                "chunk_id": f"{meta['doc_id']}#{heading['section_id']}",
                "doc_id": meta["doc_id"],
                "document_title": meta["title"],
                "version": meta["version"],
                "section_id": heading["section_id"],
                "heading_path": [meta["title"], heading["heading"]],
                "quote": [],
                "valid_from": meta["valid_from"],
                "valid_to": meta["valid_to"],
            }
            sections[current["chunk_id"]] = current
        elif current is not None:
            current["quote"].append(line)
    for record in sections.values():
        record["quote"] = "\n".join(record["quote"]).strip()
    return sections


# --- HTTP -----------------------------------------------------------------------------------


def post_json(url: str, body: dict, request_id: str, timeout: float) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "X-Request-ID": request_id},
    )
    return {"request_id": request_id, **_exchange(request, timeout)}


def get_json(url: str, timeout: float) -> dict:
    return _exchange(urllib.request.Request(url), timeout)


def _exchange(request: urllib.request.Request, timeout: float) -> dict:
    started = time.perf_counter()
    status, raw, transport_error = None, None, None
    try:
        with urllib.request.urlopen(request, timeout=timeout) as reply:
            status, raw = reply.status, reply.read()
    except urllib.error.HTTPError as error:
        # A non-2xx reply is still the API's answer: keep its status and body.
        with error:
            status, raw = error.code, error.read()
    except OSError as error:
        # Refused connection, DNS failure or timeout (URLError and TimeoutError are OSErrors).
        reason = getattr(error, "reason", error)
        if isinstance(reason, TimeoutError):
            transport_error = f"timeout after {timeout} s"
        else:
            transport_error = f"{type(reason).__name__}: {reason}"
    response, raw_body = _parse(raw)
    return {
        "http_status": status,
        "elapsed_ms": round((time.perf_counter() - started) * 1000),
        "response": response,
        "raw_body": raw_body,
        "transport_error": transport_error,
    }


def _parse(raw: bytes | None) -> tuple[object, str | None]:
    if raw is None:
        return None, None
    try:
        return json.loads(raw.decode("utf-8")), None
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, raw.decode("utf-8", errors="replace")


# --- Checks ---------------------------------------------------------------------------------


def expected_status(question: dict, mode: str) -> str | None:
    if mode == "generative":
        return question["expected_status"]
    # Evidence-only mode returns candidate sections and never decides whether they answer the
    # question, so it is expected to return candidates where the documents hold the answer and
    # its status is not judged elsewhere.
    return "evidence_only" if question["expected_source_ids"] else None


def check_question(question: dict, exchange: dict, mode: str, sections: dict) -> dict:
    """Automatic checks of one question: "pass", "fail", "n/a" (does not apply to this question
    in this mode) or "not_evaluable" (applies, but the API returned no usable answer)."""
    body = exchange["response"]
    usable = (
        exchange["http_status"] == 200
        and isinstance(body, dict)
        and "status" in body
        and body.get("request_id") == exchange["request_id"]
    )
    applicable = _applicable_checks(question, mode)
    problems = _find_problems(question, body, mode, sections) if usable else {}
    cites_something = usable and bool(body["sources"] or body["evidence"])

    checks = {"http": "pass" if usable else "fail"}
    for name in CHECK_NAMES[1:]:
        if not applicable[name] or (name == "source_validity" and usable and not cites_something):
            checks[name] = "n/a"
        elif not usable:
            checks[name] = "not_evaluable"
        else:
            checks[name] = "fail" if problems[name] else "pass"
    listed = [] if usable else [f"http: {describe_failure(exchange)}"]
    listed += [
        f"{name}: {problem}"
        for name in CHECK_NAMES[1:]
        if checks[name] == "fail"
        for problem in problems[name]
    ]
    return {
        "id": question["id"],
        "category": question["category"],
        "request_id": exchange["request_id"],
        "http_status": exchange["http_status"],
        "elapsed_ms": exchange["elapsed_ms"],
        "expected_status": expected_status(question, mode),
        "actual_status": actual_status(exchange),
        "checks": checks,
        "problems": listed,
        "human_review": "pending",
    }


def _applicable_checks(question: dict, mode: str) -> dict[str, bool]:
    generative = mode == "generative"
    expected_ids = question["expected_source_ids"]
    return {
        "status": expected_status(question, mode) is not None,
        "retrieval": bool(expected_ids),
        "citation": generative and bool(expected_ids),
        "version": bool(question["expected_versions"]),
        "source_validity": True,
        # Answerability is decided only in generative mode; evidence-only never refuses or claims.
        "no_unnecessary_refusal": generative
        and question["expected_status"] in ("answered", "partial"),
        "no_claims_when_unanswerable": generative
        and question["expected_status"] == "insufficient_evidence",
        "required_facts": generative and _has_pattern(question["required_facts"]),
        "forbidden_facts": generative and _has_pattern(question["forbidden_facts"]),
    }


def _has_pattern(facts: list[dict]) -> bool:
    return any(fact["pattern"] for fact in facts)


def _find_problems(question: dict, body: dict, mode: str, sections: dict) -> dict:
    expected_ids = question["expected_source_ids"]
    wanted_status = expected_status(question, mode)
    cited = {source["chunk_id"] for source in body["sources"]}
    # Facts are looked for in the claims only: a missing-topic sentence may repeat the question
    # (e.g. "Germany, 30 days") without asserting anything.
    claims_text = "\n".join(claim["text"] for claim in body["claims"])
    return {
        "status": (
            []
            if body["status"] == wanted_status
            else [f"{body['status']}, beklenen {wanted_status}"]
        ),
        "retrieval": [
            f"{chunk_id} ilk k'da yok"
            for chunk_id in expected_ids
            if chunk_id not in body["retrieved_chunk_ids"]
        ],
        "citation": [
            f"{chunk_id} kaynak gösterilmedi" for chunk_id in expected_ids if chunk_id not in cited
        ],
        "version": _version_problems(question["expected_versions"], body["version_decisions"]),
        "source_validity": _source_problems(body, sections),
        "no_unnecessary_refusal": (
            ["insufficient_evidence döndü"] if body["status"] == "insufficient_evidence" else []
        ),
        "no_claims_when_unanswerable": (
            [f"{len(body['claims'])} claim üretildi"] if body["claims"] else []
        ),
        "required_facts": [
            f"bulunamadı: {fact['fact']}"
            for fact in question["required_facts"]
            if fact["pattern"] and not re.search(fact["pattern"], claims_text, re.IGNORECASE)
        ],
        "forbidden_facts": [
            f"bulundu: {fact['fact']}"
            for fact in question["forbidden_facts"]
            if fact["pattern"] and re.search(fact["pattern"], claims_text, re.IGNORECASE)
        ],
    }


def _version_problems(expected_versions: dict, decisions: list[dict]) -> list[str]:
    by_procedure = {decision["procedure_id"]: decision for decision in decisions}
    problems = []
    for procedure_id, expected in expected_versions.items():
        decision = by_procedure.get(procedure_id)
        if decision is None:
            problems.append(f"{procedure_id} için sürüm kararı yok")
            continue
        selected = (decision["selected"] or {}).get("doc_id")
        if selected != expected["selected"]:
            problems.append(f"{procedure_id}: seçilen {selected}, beklenen {expected['selected']}")
        excluded = {item["doc_id"]: item["reason"] for item in decision["excluded"]}
        for doc_id, reason in expected["excluded"].items():
            if excluded.get(doc_id) != reason:
                problems.append(
                    f"{procedure_id}: {doc_id} dışlama nedeni {excluded.get(doc_id)}, "
                    f"beklenen {reason}"
                )
    return problems


SOURCE_FIELDS = ("doc_id", "document_title", "version", "section_id", "heading_path")
SOURCE_DATES = ("valid_from", "valid_to")


def _source_problems(body: dict, sections: dict) -> list[str]:
    retrieved = set(body["retrieved_chunk_ids"])
    selected = {d["selected"]["doc_id"] for d in body["version_decisions"] if d["selected"]}
    problems = []
    for item in body["sources"] + body["evidence"]:
        chunk_id = item["chunk_id"]
        record = sections.get(chunk_id)
        if record is None:
            problems.append(f"{chunk_id} korpusta böyle bir bölüm yok")
        else:
            problems += [
                f"{chunk_id} {field} bölüm kaydıyla aynı değil"
                for field in SOURCE_FIELDS + SOURCE_DATES
                if item.get(field) != record[field]
            ]
            if item["quote"] != record["quote"]:
                problems.append(f"{chunk_id} alıntısı o bölümün birebir metni değil")
        if not item["quote"].strip():
            problems.append(f"{chunk_id} alıntısı boş")
        if chunk_id not in retrieved:
            problems.append(f"{chunk_id} getirilen bölümler arasında değil")
        if chunk_id != f"{item['doc_id']}#{item['section_id']}":
            problems.append(f"{chunk_id} doc_id/section_id ile uyuşmuyor")
        if item["doc_id"] not in selected:
            problems.append(f"{chunk_id} seçili sürümden değil")
    cited = {chunk_id for claim in body["claims"] for chunk_id in claim["source_chunk_ids"]}
    if cited != {source["chunk_id"] for source in body["sources"]}:
        problems.append("claim atıfları ile sources aynı değil")
    return problems


def actual_status(exchange: dict) -> str:
    body = exchange["response"]
    if exchange["transport_error"]:
        return "transport_error"
    if exchange["http_status"] == 200 and isinstance(body, dict) and "status" in body:
        return body["status"]
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        return f"error:{body['error'].get('code')}"
    return f"http_{exchange['http_status']}"


def describe_failure(exchange: dict) -> str:
    if exchange["transport_error"]:
        return exchange["transport_error"]
    body = exchange["response"]
    if exchange["http_status"] == 200 and isinstance(body, dict):
        return f"request_id {body.get('request_id')}, gönderilen {exchange.get('request_id')}"
    return f"HTTP {exchange['http_status']} {actual_status(exchange)}"


def summarize(checked: list[dict]) -> dict:
    """Per check: passes over the questions it applies to, and which failed or had no answer."""
    summary = {}
    for name in CHECK_NAMES:
        outcomes = [(item["id"], item["checks"][name]) for item in checked]
        summary[name] = {
            "passed": sum(outcome == "pass" for _, outcome in outcomes),
            "applicable": sum(outcome != "n/a" for _, outcome in outcomes),
            "failed": [qid for qid, outcome in outcomes if outcome == "fail"],
            "not_evaluable": [qid for qid, outcome in outcomes if outcome == "not_evaluable"],
        }
    return summary


def git_state() -> dict:
    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()

    changed = git("status", "--porcelain", "--", *RUN_INPUTS).splitlines()
    return {
        "commit": git("rev-parse", "HEAD"),
        "dirty": bool(changed),
        "dirty_paths": [line[3:] for line in changed],
    }


# --- Report ---------------------------------------------------------------------------------


def render_report(
    metadata: dict,
    questions: list[dict],
    exchanges: list[dict],
    checked: list[dict],
    summary: dict,
    multi_summary: dict,
) -> str:
    ready = metadata["readiness"]
    git = metadata["git"]
    threshold = "kapalı" if ready["min_retrieval_score"] is None else ready["min_retrieval_score"]
    unchanged = "evet" if metadata["readiness_unchanged"] else "HAYIR"
    lines = [
        f"# Değerlendirme raporu: `{metadata['run_id']}`",
        "",
        "Bu dosyayı `eval/run_eval.py` üretti. Otomatik kontroller durumları, bölüm kimliklerini, "
        "sürüm kararlarını, alıntıları ve claim metinlerinde birkaç düzenli ifadeyi karşılaştırır; "
        "anlamsal doğruluğu ölçmez. Her sorunun insan incelemesi `pending` başlar.",
        "",
        "## Koşu bilgileri",
        "",
        "| Alan | Değer |",
        "|---|---|",
        f"| Gerçek çalıştırma zamanı | {metadata['started_at']} → {metadata['finished_at']} |",
        f"| Mod | `{metadata['mode']}` |",
        f"| API | `{metadata['api']}/api/ask`, istek başına {metadata['request_timeout_seconds']} "
        "sn timeout |",
        f"| Commit | `{git['commit']}`; koşu girdileri commit'ten farklı (dirty): "
        f"{'evet ' + ', '.join(git['dirty_paths']) if git['dirty'] else 'hayır'} |",
        f"| Soru sayısı | {metadata['question_count']} |",
        f"| Corpus fingerprint | `{ready['corpus_fingerprint']}` |",
        f"| Embedding | `{ready['embedding_model']}@{ready['embedding_revision']}` |",
        f"| LLM modeli (yapılandırılan) | `{ready['llm_model']}`; "
        f"generation_configured={str(ready['generation_configured']).lower()} |",
        f"| Prompt | `{ready['prompt_version']}`, SHA-256 `{ready['prompt_hash']}` |",
        f"| top_k / skor eşiği | {ready['top_k']} / {threshold} |",
        f"| Readiness koşu sonunda aynı | {unchanged} |",
        "",
        metadata["as_of_note"],
        "",
        "## Otomatik ölçümler",
        "",
        "Payda, kontrolün o soru ve modda uygulandığı sorulardır (tanımlar `docs/project-spec.md` "
        "§7). Değerlendirilemeyen: kontrol uygulanıyor ama API kullanılabilir bir cevap dönmedi.",
        "",
        "| Ölçüm | Geçen / uygulanan | Başarısız | Değerlendirilemeyen |",
        "|---|---|---|---|",
    ]
    rows = [(CHECK_LABELS[name], summary[name]) for name in CHECK_NAMES]
    rows += [
        (f"Çok kaynaklı sorular: {CHECK_LABELS[name]}", multi_summary[name])
        for name in ("retrieval", "citation")
    ]
    for label, counts in rows:
        lines.append(
            f"| {label} | {counts['passed']} / {counts['applicable']} | "
            f"{', '.join(counts['failed']) or '—'} | {', '.join(counts['not_evaluable']) or '—'} |"
        )
    lines += [
        "",
        "## Soru bazında özet",
        "",
        "| ID | Kategori | Beklenen durum | Gerçek | Beklenen bölüm | İlk k | Kaynak / aday | "
        "Başarısız kontroller | İnsan incelemesi |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for question, exchange, item in zip(questions, exchanges, checked, strict=True):
        body = exchange["response"] if item["checks"]["http"] == "pass" else None
        failed = [name for name, outcome in item["checks"].items() if outcome == "fail"]
        lines.append(
            f"| {item['id']} | {item['category']} | {item['expected_status'] or '—'} | "
            f"{item['actual_status']} | {', '.join(question['expected_source_ids']) or '—'} | "
            f"{_ids(body, 'retrieved')} | {_ids(body, 'cited')} | {', '.join(failed) or '—'} | "
            f"{item['human_review']} |"
        )
    lines += ["", "## Ayrıntılar", ""]
    for question, exchange, item in zip(questions, exchanges, checked, strict=True):
        lines += _question_details(question, exchange, item)
    return "\n".join(lines) + "\n"


def _ids(body: dict | None, kind: str) -> str:
    if body is None:
        return "—"
    if kind == "retrieved":
        ids = body["retrieved_chunk_ids"]
    else:
        ids = [item["chunk_id"] for item in body["sources"] + body["evidence"]]
    return ", ".join(ids) or "—"


def _question_details(question: dict, exchange: dict, item: dict) -> list[str]:
    request = exchange["request"]
    lines = [
        f"### {item['id']} · {item['category']}",
        "",
        f"- Soru: {request['question']}",
        *(
            [f"- Soru sürümü: {question['revision']} (önceki sürümler `revisions` alanında)"]
            if "revision" in question
            else []
        ),
        f"- İstek: as_of `{request['as_of']}`, kapsam "
        f"`{'/'.join(request['scope'].values())}`, mod `{request['mode']}`",
        f"- Beklenen (üretken mod): `{question['expected_status']}`; bölümler "
        f"{', '.join(question['expected_source_ids']) or '—'}. Rubrik: {question['rubric']}",
    ]
    lines += [f"  - Gerekli: {fact['fact']}" for fact in question["required_facts"]]
    lines += [f"  - Yasak: {fact['fact']}" for fact in question["forbidden_facts"]]
    body = exchange["response"]
    lines.append(
        f"- Gerçek: HTTP {exchange['http_status']}, `{item['actual_status']}`, "
        f"{exchange['elapsed_ms']} ms"
    )
    if item["checks"]["http"] == "pass":
        lines.append(f"  - İlk k: {_ids(body, 'retrieved')}; kaynak/aday: {_ids(body, 'cited')}")
        lines.append(f"  - reason_code: {body['reason_code'] or '—'}")
        for claim in body["claims"]:
            lines.append(f"  - Claim: {claim['text']} [{', '.join(claim['source_chunk_ids'])}]")
        lines += [f"  - Eksik konu: {topic}" for topic in body["missing_topics"]]
        if body["answer"]:
            lines.append(f"  - Cevap: {body['answer']}")
        lines.append(f"  - Sürüm kararları: {_decisions(body['version_decisions']) or '—'}")
    elif exchange["transport_error"]:
        lines.append(f"  - Bağlantı hatası: {exchange['transport_error']}")
    else:
        lines.append(
            f"  - Gövde: `{json.dumps(body, ensure_ascii=False) if body else exchange['raw_body']}`"
        )
    lines += [f"- Kontrol sorunu: {problem}" for problem in item["problems"]]
    lines += [f"- İnsan incelemesi: {item['human_review']}", ""]
    return lines


def _decisions(decisions: list[dict]) -> str:
    parts = []
    for decision in decisions:
        selected = (decision["selected"] or {}).get("doc_id", "yok")
        excluded = ", ".join(f"{e['doc_id']} {e['reason']}" for e in decision["excluded"])
        parts.append(
            f"{decision['procedure_id']} → {selected}" + (f" ({excluded})" if excluded else "")
        )
    return "; ".join(parts)


if __name__ == "__main__":
    sys.exit(main())
