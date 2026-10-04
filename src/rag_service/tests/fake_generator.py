"""Stands in for the language model in default (offline) tests.

It returns a prepared model answer or raises a prepared error, and records exactly what the
service sent. It is a test tool only: it shows what the service does with a given model output,
not how a real model behaves (for example under prompt injection).
"""

from app.generation import Generation, GenerationError, ModelAnswer


def model_answer(
    status: str,
    claims: list[tuple[str, list[str]]] = (),
    missing_topics: list[str] = (),
    reason_code: str | None = None,
) -> ModelAnswer:
    return ModelAnswer.model_validate(
        {
            "status": status,
            "claims": [{"text": text, "source_chunk_ids": ids} for text, ids in claims],
            "missing_topics": list(missing_topics),
            "reason_code": reason_code,
        }
    )


class FakeGenerator:
    def __init__(self, answer: ModelAnswer | None = None, error: GenerationError | None = None):
        self.answer = answer
        self.error = error
        self.calls: list[tuple[str, str]] = []

    async def generate(self, instructions: str, user_input: str) -> Generation:
        self.calls.append((instructions, user_input))
        if self.error is not None:
            raise self.error
        assert self.answer is not None, "give the fake an answer or an error"
        return Generation(
            answer=self.answer, model="fake-model", input_tokens=None, output_tokens=None
        )
