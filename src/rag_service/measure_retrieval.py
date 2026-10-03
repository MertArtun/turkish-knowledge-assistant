"""Rank the development questions with the real local model and print raw scores as Markdown.

The development questions (eval/dev_questions.jsonl) are kept apart from the evaluation set;
retrieval and threshold decisions are tried on them first. The scores printed here are measurement
data for those decisions; the API never returns them.

Run from src/rag_service:  uv run python measure_retrieval.py [questions.jsonl]
"""

import json
import os
import sys
from pathlib import Path

from app.contracts import AskRequest
from app.documents import load_corpus
from app.embeddings import E5Embedder, embed_query
from app.index_store import load_or_build_index
from app.retrieval import retrieve
from app.settings import load_settings
from app.versioning import effective_as_of, effective_scope, select_versions

DEFAULT_QUESTIONS = Path("../../eval/dev_questions.jsonl")


def main(questions_path: Path) -> None:
    settings = load_settings(os.environ)
    documents = load_corpus(settings.knowledge_dir)
    embedder = E5Embedder(
        settings.embedding_model, settings.embedding_revision, settings.model_cache_dir
    )
    index = load_or_build_index(documents, embedder, settings.index_path)
    metadata = [doc.metadata for doc in documents]
    print(
        f"model `{embedder.model_id}`, index `{index.fingerprint[:12]}`, top_k {settings.top_k}\n"
    )

    for line in questions_path.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        request = AskRequest.model_validate(item["request"])
        expected = item["expected_source_ids"]
        as_of = effective_as_of(request.as_of)
        view = select_versions(metadata, effective_scope(request.scope), as_of)
        query_vector = embed_query(embedder, request.question)
        ranking = retrieve(index, query_vector, view, top_k=len(index.chunks))

        print(f"### {item['id']} ({item['category']}, as_of {as_of})\n")
        print(f"{request.question}\n")
        print(f"Expected: {', '.join(expected) or 'none'}\n")
        print("| rank | chunk_id | score |\n|---|---|---|")
        for rank, result in enumerate(ranking, start=1):
            if rank <= settings.top_k or result.chunk.chunk_id in expected:
                marker = " (expected)" if result.chunk.chunk_id in expected else ""
                print(f"| {rank} | {result.chunk.chunk_id}{marker} | {result.score:.4f} |")
        print()


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_QUESTIONS)
