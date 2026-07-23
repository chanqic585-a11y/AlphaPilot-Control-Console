from __future__ import annotations

import json
import unittest

from alphapilot_control_console.ai_orchestration.contracts import AIRequest, ModelIdentity
from alphapilot_control_console.ai_orchestration.provider_adapters import batch_adapters
from alphapilot_control_console.ai_orchestration.provider_adapters.batch_adapters import (
    GeminiBatchAdapter,
)


SCHEMA = {
    "type": "object",
    "properties": {"summary": {"type": "string"}},
    "required": ["summary"],
    "additionalProperties": False,
}


def _request(request_id: str) -> AIRequest:
    return AIRequest(
        request_id=request_id,
        task_type="historical_batch",
        payload={"platformPrompt": "local prompt", "untrustedData": {"id": request_id}},
        response_schema=SCHEMA,
        sensitivity="internal",
        prompt_version="historical-batch-v1",
        token_ceiling=500,
    )


class RecordingBatchTransport:
    def __init__(self) -> None:
        self.json_calls: list[dict] = []
        self.upload_calls: list[dict] = []
        self.downloads: dict[str, str] = {}
        self.responses: list[dict] = []

    def request_json(self, **kwargs: object) -> dict:
        self.json_calls.append(dict(kwargs))
        return self.responses.pop(0)

    def upload_jsonl(self, **kwargs: object) -> dict:
        self.upload_calls.append(dict(kwargs))
        return self.responses.pop(0)

    def download_text(self, **kwargs: object) -> str:
        return self.downloads[str(kwargs["url"])]


class BatchProviderAdapterTests(unittest.TestCase):
    def test_no_deepseek_or_openai_batch_adapter_is_claimed(self) -> None:
        self.assertFalse(hasattr(batch_adapters, "DeepSeekBatchAdapter"))
        self.assertFalse(hasattr(batch_adapters, "OpenAIBatchAdapter"))

    def test_gemini_uses_inline_batch_generate_content_and_reconciles_outputs(self) -> None:
        transport = RecordingBatchTransport()
        transport.responses = [
            {"name": "batches/gemini-1", "state": "JOB_STATE_PENDING"},
            {
                "name": "batches/gemini-1",
                "state": "JOB_STATE_SUCCEEDED",
                "dest": {
                    "inlinedResponses": [
                        {
                            "metadata": {"key": "one"},
                            "response": {
                                "candidates": [
                                    {
                                        "content": {
                                            "parts": [{"text": json.dumps({"summary": "ok"})}]
                                        }
                                    }
                                ]
                            },
                        }
                    ]
                },
            },
        ]
        adapter = GeminiBatchAdapter(transport=transport, api_key="process-only")
        identity = ModelIdentity("gemini_batch", "gemini", "configured-gemini", frozenset())

        submitted = adapter.submit(identity, [_request("one")], payload_hash="sha256:payload")
        status = adapter.get_status(submitted.provider_job_id)

        create = transport.json_calls[0]
        self.assertTrue(
            str(create["url"]).endswith(
                "/v1beta/models/configured-gemini:batchGenerateContent"
            )
        )
        first = create["json_body"]["batch"]["input_config"]["requests"]["requests"][0]
        self.assertEqual(first["metadata"]["key"], "one")
        self.assertEqual(status.status, "completed")
        self.assertEqual(status.outputs, {"one": {"summary": "ok"}})


if __name__ == "__main__":
    unittest.main()
