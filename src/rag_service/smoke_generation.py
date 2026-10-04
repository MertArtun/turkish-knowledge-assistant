"""Live smoke check of the generative path: exactly two real, paid model calls, run by hand only.

Loads the real corpus, embedding model and index, then asks two development questions in
generative mode: one the documents answer (DEV02) and one they do not (DEV04). It prints what the
API would return and the service's generation log line (the model the provider reports, token
usage, timing). It is never part of the default tests and is not an evaluation.

Run from src/rag_service; the key is read from ../../.env and never printed:
    uv run --env-file ../../.env python smoke_generation.py
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from app.contracts import AskRequest
from app.service import AskError, load_assistant
from app.settings import load_settings

DEV_QUESTIONS = Path("../../eval/dev_questions.jsonl")
SMOKE_IDS = ("DEV02", "DEV04")


async def main() -> int:
    settings = load_settings(os.environ)
    if settings.openai_api_key is None:
        print("not run: OPENAI_API_KEY is not set; no provider call was made")
        return 2
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    assistant = load_assistant(settings)
    print(
        f"endpoint {settings.openai_base_url.host}, model {settings.openai_model}, "
        f"prompt {assistant.prompt.version}@{assistant.prompt.sha256[:12]}\n"
    )

    items = [json.loads(line) for line in DEV_QUESTIONS.read_text(encoding="utf-8").splitlines()]
    for item in (item for item in items if item["id"] in SMOKE_IDS):
        request = AskRequest.model_validate({**item["request"], "mode": "generative"})
        print(f"--- {item['id']} ({item['category']}): {request.question}")
        try:
            response = await assistant.ask(request, f"smoke-{item['id']}")
        except AskError as error:
            print(f"error {error.code}: {error.message}\n")
            continue
        summary = response.model_dump(
            mode="json",
            include={"status", "answer", "claims", "missing_topics", "reason_code"},
        )
        summary["sources"] = [source.chunk_id for source in response.sources]
        summary["retrieved_chunk_ids"] = response.retrieved_chunk_ids
        print(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
