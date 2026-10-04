"""Tests of the evaluation runner's checks and HTTP recording.

Run from the repository root (stdlib only):  python3 -m unittest discover -s eval -v
"""

import json
import re
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import run_eval

SCOPE = {"country": "TR", "customer_type": "B2B", "product": "MH-10"}
D04_SURE = "İade talebi, ürünün tesliminden itibaren 30 takvim günü içinde açılabilir."
D04_TARIHLER = "İade süresi ürünün teslim tarihinden itibaren sayılır."
D03_SURE = "İade talebi, ürünün tesliminden itibaren 14 takvim günü içinde açılabilir."


def document(doc_id, version, valid_from, valid_to, body):
    return (
        f"---\ndoc_id: {doc_id}\nprocedure_id: returns\ntitle: MH-10 İade Prosedürü\n"
        f'version: "{version}"\nvalid_from: {valid_from}\nvalid_to: {valid_to}\n---\n\n{body}'
    )


SECTIONS = {
    **run_eval.parse_document(
        document(
            "D03", "1.0", "2026-01-01", "2026-07-01", f"## İade süresi {{#sure}}\n\n{D03_SURE}\n"
        )
    ),
    **run_eval.parse_document(
        document(
            "D04",
            "2.0",
            "2026-07-01",
            "null",
            f"## İade süresi {{#sure}}\n\n{D04_SURE}\n\n"
            f"## İki tarihin farkı {{#tarihler}}\n\n{D04_TARIHLER}\n",
        )
    ),
}
RETURNS_D04 = {
    "procedure_id": "returns",
    "selected": {"doc_id": "D04", "version": "2.0", "valid_from": "2026-07-01", "valid_to": None},
    "excluded": [
        {
            "doc_id": "D03",
            "version": "1.0",
            "valid_from": "2026-01-01",
            "valid_to": "2026-07-01",
            "reason": "expired",
        }
    ],
}
QUESTION = {
    "id": "E03",
    "category": "version_conflict",
    "request": {"question": "Kulaklığı kaç gün içinde iade edebilirim?", "as_of": "2026-10-04"},
    "expected_status": "answered",
    "required_facts": [{"fact": "30 takvim günü", "pattern": r"\b30\b"}],
    "forbidden_facts": [{"fact": "14 takvim günü (eski sürüm)", "pattern": r"\b14\b"}],
    "expected_source_ids": ["D04#sure"],
    "expected_versions": {"returns": {"selected": "D04", "excluded": {"D03": "expired"}}},
    "rubric": "30 takvim günü; 14 değil.",
}
UNANSWERABLE = {
    **QUESTION,
    "id": "E12",
    "category": "unanswerable",
    "expected_status": "insufficient_evidence",
    "required_facts": [],
    "forbidden_facts": [{"fact": "Türkiye kuralını Almanya'ya uygulamak", "pattern": "Almanya"}],
    "expected_source_ids": [],
    "expected_versions": {},
}


def section(chunk_id, **changes):
    """A source/evidence object exactly as the API builds it from the corpus, optionally altered."""
    return {**SECTIONS[chunk_id], **changes}


def answered(**changes):
    body = {
        "request_id": "eval.run.E03",
        "status": "answered",
        "mode": "generative",
        "effective_as_of": "2026-10-04",
        "effective_scope": SCOPE,
        "answer": "İade talebi teslimden itibaren 30 takvim günü içinde açılabilir.",
        "claims": [
            {
                "text": "İade talebi teslimden itibaren 30 takvim günü içinde açılabilir.",
                "source_chunk_ids": ["D04#sure"],
            }
        ],
        "sources": [section("D04#sure")],
        "evidence": [],
        "missing_topics": [],
        "reason_code": None,
        "version_decisions": [RETURNS_D04],
        "retrieved_chunk_ids": ["D04#sure", "D04#tarihler", "D05#bedel", "D04#uygulama"],
    }
    body.update(changes)
    return body


def insufficient(**changes):
    return answered(
        status="insufficient_evidence",
        answer="Belgeler yalnızca isteğin kapsamı için geçerlidir.",
        claims=[],
        sources=[],
        reason_code="unsupported_scope",
        **changes,
    )


def exchange(body, http_status=200):
    return {
        "request_id": "eval.run.E03",
        "http_status": http_status,
        "elapsed_ms": 12,
        "response": body,
        "raw_body": None,
        "transport_error": None,
    }


def check(question, body, mode="generative", http_status=200):
    return run_eval.check_question(question, exchange(body, http_status), mode, SECTIONS)


class CheckQuestionTests(unittest.TestCase):
    def test_correct_cited_answer_passes_every_applicable_check(self):
        result = check(QUESTION, answered())

        self.assertEqual(result["actual_status"], "answered")
        self.assertEqual(result["problems"], [])
        self.assertEqual(
            result["checks"],
            {
                "http": "pass",
                "status": "pass",
                "retrieval": "pass",
                "citation": "pass",
                "version": "pass",
                "source_validity": "pass",
                "no_unnecessary_refusal": "pass",
                "no_claims_when_unanswerable": "n/a",
                "required_facts": "pass",
                "forbidden_facts": "pass",
            },
        )
        self.assertEqual(result["human_review"], "pending")

    def test_wrong_number_behind_the_right_source_passes_source_checks_only(self):
        # The source check is not a meaning check: only the limited fact patterns notice it.
        claim = {"text": "İade süresi 14 takvim günüdür.", "source_chunk_ids": ["D04#sure"]}
        result = check(QUESTION, answered(claims=[claim]))

        self.assertEqual(result["checks"]["citation"], "pass")
        self.assertEqual(result["checks"]["source_validity"], "pass")
        self.assertEqual(result["checks"]["required_facts"], "fail")
        self.assertEqual(result["checks"]["forbidden_facts"], "fail")

    def test_http_error_fails_the_http_check_and_leaves_the_rest_not_evaluable(self):
        body = {
            "request_id": "eval.run.E03",
            "error": {"code": "invalid_generation_output", "message": "..."},
        }
        result = check(QUESTION, body, http_status=502)

        self.assertEqual(result["actual_status"], "error:invalid_generation_output")
        self.assertEqual(result["checks"]["http"], "fail")
        self.assertEqual(result["checks"]["status"], "not_evaluable")
        self.assertEqual(result["checks"]["retrieval"], "not_evaluable")
        self.assertEqual(result["checks"]["no_claims_when_unanswerable"], "n/a")

    def test_transport_failure_is_recorded_as_such(self):
        failed = {**exchange(None, None), "transport_error": "timeout after 60 s"}
        result = run_eval.check_question(QUESTION, failed, "generative", SECTIONS)

        self.assertEqual(result["actual_status"], "transport_error")
        self.assertEqual(result["checks"]["http"], "fail")

    def test_response_for_another_request_id_fails_the_http_check(self):
        result = check(QUESTION, answered(request_id="someone-else"))

        self.assertEqual(result["checks"]["http"], "fail")

    def test_evidence_only_expects_candidates_and_does_not_judge_answerability(self):
        evidence_body = answered(
            status="evidence_only",
            mode="evidence_only",
            answer=None,
            claims=[],
            sources=[],
            evidence=[section("D04#sure"), section("D04#tarihler")],
            retrieved_chunk_ids=["D04#sure", "D04#tarihler"],
        )
        answerable = check(QUESTION, evidence_body, mode="evidence_only")
        unanswerable = check(UNANSWERABLE, evidence_body, mode="evidence_only")

        self.assertEqual(answerable["expected_status"], "evidence_only")
        self.assertEqual(answerable["checks"]["status"], "pass")
        self.assertEqual(answerable["checks"]["citation"], "n/a")
        self.assertEqual(answerable["checks"]["required_facts"], "n/a")
        self.assertEqual(unanswerable["expected_status"], None)
        self.assertEqual(unanswerable["checks"]["status"], "n/a")
        self.assertEqual(unanswerable["checks"]["no_claims_when_unanswerable"], "n/a")
        self.assertEqual(answerable["checks"]["no_unnecessary_refusal"], "n/a")

    def test_refusal_of_an_answerable_question_is_an_unnecessary_refusal(self):
        result = check(QUESTION, insufficient())

        self.assertEqual(result["checks"]["no_unnecessary_refusal"], "fail")
        self.assertEqual(result["checks"]["status"], "fail")
        self.assertEqual(result["checks"]["citation"], "fail")
        self.assertEqual(result["checks"]["retrieval"], "pass")

    def test_claims_for_an_unanswerable_question_are_counted_as_claims(self):
        claim = {"text": "Almanya'da da 30 gün geçerlidir.", "source_chunk_ids": ["D04#sure"]}
        result = check(UNANSWERABLE, answered(claims=[claim]))

        self.assertEqual(result["checks"]["no_claims_when_unanswerable"], "fail")
        self.assertEqual(result["checks"]["forbidden_facts"], "fail")
        self.assertEqual(result["checks"]["no_unnecessary_refusal"], "n/a")

    def test_fact_patterns_are_searched_in_claims_not_in_missing_topics(self):
        # A missing topic may repeat the question; it asserts nothing.
        body = insufficient(missing_topics=["Almanya'daki müşteriler için 30 günlük süre"])
        result = check(UNANSWERABLE, body)

        self.assertEqual(result["checks"]["forbidden_facts"], "pass")
        self.assertEqual(result["checks"]["status"], "pass")

    def test_expired_version_selected_fails_the_version_and_source_checks(self):
        returns_d03 = {
            "procedure_id": "returns",
            "selected": {
                "doc_id": "D03",
                "version": "1.0",
                "valid_from": "2026-01-01",
                "valid_to": "2026-07-01",
            },
            "excluded": [],
        }
        body = answered(
            claims=[{"text": "14 takvim günü.", "source_chunk_ids": ["D03#sure"]}],
            sources=[section("D03#sure")],
            retrieved_chunk_ids=["D03#sure"],
            version_decisions=[RETURNS_D04],
        )

        self.assertEqual(check(QUESTION, body)["checks"]["source_validity"], "fail")
        self.assertEqual(
            check(QUESTION, answered(version_decisions=[returns_d03]))["checks"]["version"], "fail"
        )
        self.assertEqual(
            check(QUESTION, answered(version_decisions=[]))["checks"]["version"], "fail"
        )
        wrong_reason = {
            **RETURNS_D04,
            "excluded": [{**RETURNS_D04["excluded"][0], "reason": "not_approved"}],
        }
        self.assertEqual(
            check(QUESTION, answered(version_decisions=[wrong_reason]))["checks"]["version"], "fail"
        )

    def test_source_outside_the_retrieved_sections_or_with_a_changed_quote_is_invalid(self):
        not_retrieved = answered(retrieved_chunk_ids=["D04#tarihler"])
        changed_quote = answered(sources=[section("D04#sure", quote=D04_SURE.replace("30", "60"))])
        wrong_section = answered(sources=[section("D04#sure", section_id="kargo")])

        for body in (not_retrieved, changed_quote, wrong_section):
            self.assertEqual(check(QUESTION, body)["checks"]["source_validity"], "fail")

    def test_answer_without_sources_or_candidates_leaves_source_validity_not_applicable(self):
        # Nothing was cited, so there is nothing whose validity could pass or fail.
        result = check(UNANSWERABLE, insufficient())

        self.assertEqual(result["checks"]["source_validity"], "n/a")


class SourceCheckAgainstRealCorpusTests(unittest.TestCase):
    """Quotes are compared with the cited section of the real corpus, not with the whole file."""

    @classmethod
    def setUpClass(cls):
        cls.sections = run_eval.load_sections(run_eval.KNOWLEDGE_DIR)

    def body_citing(self, *items):
        return answered(
            claims=[{"text": "…", "source_chunk_ids": [item["chunk_id"] for item in items]}],
            sources=list(items),
            retrieved_chunk_ids=[item["chunk_id"] for item in items],
        )

    def source_validity(self, *items):
        result = run_eval.check_question(
            QUESTION, exchange(self.body_citing(*items)), "generative", self.sections
        )
        problems = [p for p in result["problems"] if p.startswith("source_validity:")]
        return result["checks"]["source_validity"], problems

    def test_real_section_cited_as_the_api_builds_it_passes(self):
        self.assertEqual(self.source_validity(dict(self.sections["D04#sure"])), ("pass", []))

    def test_quote_of_another_section_under_this_section_id_fails(self):
        item = {**self.sections["D04#sure"], "quote": self.sections["D04#kargo"]["quote"]}

        self.assertEqual(self.source_validity(item)[0], "fail")

    def test_empty_quote_fails(self):
        item = {**self.sections["D04#sure"], "quote": ""}

        self.assertEqual(self.source_validity(item)[0], "fail")

    def test_section_missing_from_the_corpus_fails_even_when_repeated_consistently(self):
        item = {
            **self.sections["D04#sure"],
            "chunk_id": "D04#yok",
            "section_id": "yok",
        }

        self.assertEqual(self.source_validity(item)[0], "fail")

    def test_metadata_that_differs_from_the_section_record_fails(self):
        changes = (("version", "1.0"), ("valid_to", "2027-01-01"), ("heading_path", ["x"]))
        for field, value in changes:
            item = {**self.sections["D04#sure"], field: value}
            self.assertEqual(self.source_validity(item)[0], "fail", field)

    def test_section_reader_matches_the_supported_document_format(self):
        record = self.sections["D04#kargo"]

        self.assertEqual(record["doc_id"], "D04")
        self.assertEqual(record["version"], "2.0")
        self.assertIsNone(record["valid_to"])
        self.assertEqual(record["heading_path"][0], "MH-10 İade Prosedürü")
        self.assertTrue(record["quote"].startswith("Şirket"))
        self.assertNotIn("##", record["quote"])


class SummaryTests(unittest.TestCase):
    def test_counts_passes_over_applicable_questions_and_lists_the_rest(self):
        checked = [
            check(QUESTION, answered()),
            {**check(QUESTION, insufficient()), "id": "E16"},
            {
                **check(QUESTION, {"error": {"code": "provider_unavailable"}}, http_status=503),
                "id": "E18",
            },
            check(UNANSWERABLE, insufficient()),
        ]

        summary = run_eval.summarize(checked)

        self.assertEqual(
            summary["no_unnecessary_refusal"],
            {"passed": 1, "applicable": 3, "failed": ["E16"], "not_evaluable": ["E18"]},
        )
        self.assertEqual(
            summary["no_claims_when_unanswerable"],
            {"passed": 1, "applicable": 1, "failed": [], "not_evaluable": []},
        )
        self.assertEqual(summary["http"]["passed"], 3)
        self.assertEqual(summary["http"]["applicable"], 4)


class RecordingTests(unittest.TestCase):
    """Every HTTP exchange is kept as real output, including errors and timeouts."""

    @classmethod
    def setUpClass(cls):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers["Content-Length"])
                sent = json.loads(self.rfile.read(length))
                if sent["question"] == "slow":
                    time.sleep(1.5)
                body = json.dumps(
                    {
                        "request_id": self.headers["X-Request-ID"],
                        "error": {"code": "upstream_unavailable", "message": "Hizmet hazır değil."},
                    },
                    ensure_ascii=False,
                ).encode()
                status = 503 if sent["question"] != "not-json" else 502
                if sent["question"] == "not-json":
                    body = b"<html>bad gateway</html>"
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/api/ask"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_error_status_and_body_are_recorded(self):
        recorded = run_eval.post_json(self.url, {"question": "q"}, "eval.x.E01", timeout=5)

        self.assertEqual(recorded["http_status"], 503)
        self.assertEqual(recorded["response"]["error"]["code"], "upstream_unavailable")
        self.assertEqual(recorded["response"]["request_id"], "eval.x.E01")
        self.assertIsNone(recorded["transport_error"])

    def test_body_that_is_not_json_is_kept_raw(self):
        recorded = run_eval.post_json(self.url, {"question": "not-json"}, "eval.x.E02", timeout=5)

        self.assertEqual(recorded["http_status"], 502)
        self.assertIsNone(recorded["response"])
        self.assertEqual(recorded["raw_body"], "<html>bad gateway</html>")

    def test_client_timeout_is_recorded_as_a_transport_error(self):
        recorded = run_eval.post_json(self.url, {"question": "slow"}, "eval.x.E03", timeout=0.3)

        self.assertIsNone(recorded["http_status"])
        self.assertIn("timeout", recorded["transport_error"])

    def test_refused_connection_is_recorded_as_a_transport_error(self):
        closed = ThreadingHTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
        url = f"http://127.0.0.1:{closed.server_port}/api/ask"
        closed.server_close()

        recorded = run_eval.post_json(url, {"question": "q"}, "eval.x.E04", timeout=2)

        self.assertIsNone(recorded["http_status"])
        self.assertIsNotNone(recorded["transport_error"])


class QuestionSetTests(unittest.TestCase):
    """The evaluation set itself: the brief's 18 questions with checkable expectations."""

    @classmethod
    def setUpClass(cls):
        cls.questions = run_eval.load_questions(run_eval.DEFAULT_QUESTIONS)
        cls.sections = run_eval.load_sections(run_eval.KNOWLEDGE_DIR)
        cls.doc_ids = {record["doc_id"] for record in cls.sections.values()}

    def test_has_e01_to_e18_dated_as_the_brief_says(self):
        self.assertEqual([q["id"] for q in self.questions], [f"E{n:02d}" for n in range(1, 19)])
        for question in self.questions:
            expected_as_of = "2026-06-01" if question["id"] == "E16" else "2026-10-04"
            self.assertEqual(question["request"]["as_of"], expected_as_of, question["id"])
            self.assertEqual(question["request"]["scope"], SCOPE, question["id"])
            self.assertNotIn("mode", question["request"], "the runner sets the mode per run")

    def test_expectations_are_well_formed_and_point_at_real_sections(self):
        statuses = {q["id"]: q["expected_status"] for q in self.questions}
        self.assertEqual(
            [i for i, s in statuses.items() if s == "insufficient_evidence"], ["E11", "E12", "E13"]
        )
        self.assertEqual([i for i, s in statuses.items() if s == "partial"], ["E15"])
        for question in self.questions:
            self.assertTrue(question["rubric"], question["id"])
            for fact in question["required_facts"] + question["forbidden_facts"]:
                self.assertTrue(fact["fact"])
                if fact["pattern"] is not None:
                    re.compile(fact["pattern"])
            for chunk_id in question["expected_source_ids"]:
                self.assertIn(chunk_id, self.sections)
            for decision in question["expected_versions"].values():
                self.assertIn(decision["selected"], self.doc_ids)
                self.assertTrue(set(decision["excluded"]) <= self.doc_ids)
        self.assertEqual(
            next(q for q in self.questions if q["id"] == "E18")["expected_source_ids"],
            ["D04#sure", "D05#bedel"],
        )

    def test_reworded_question_keeps_its_previous_text_and_reason(self):
        # E15 did not name its topic; the rewording is versioned instead of silently replaced,
        # so earlier runs stay readable as runs of the earlier question.
        e15 = next(q for q in self.questions if q["id"] == "E15")

        self.assertEqual(e15["revision"], 2)
        self.assertIn("iade", e15["request"]["question"])
        self.assertEqual(
            e15["revisions"][0]["question"], "Türkiye'de kaç günüm var; Almanya'da da aynı mı?"
        )
        self.assertTrue(e15["revisions"][0]["reason"])
        for question in self.questions:
            if "revision" not in question:
                self.assertNotIn("revisions", question, question["id"])

    def test_report_shows_the_question_revision(self):
        e15 = next(q for q in self.questions if q["id"] == "E15")
        item = check(e15, insufficient(), mode="generative")
        lines = run_eval._question_details(
            e15,
            {**exchange(insufficient()), "request": {**e15["request"], "mode": "generative"}},
            item,
        )

        self.assertIn("- Soru sürümü: 2 (önceki metinler `revisions` alanında)", lines)


if __name__ == "__main__":
    unittest.main()
