from __future__ import annotations

import json
import threading
import unittest
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

from alphapilot_control_console import http_app
from alphapilot_control_console.http_app import ConsoleHandler
from alphapilot_control_console.v63_1_ui.contracts import ProjectionConflict
from alphapilot_control_console.v63_1_ui.http import V631HttpRouter
from alphapilot_control_console.v63_1_ui.service import StateVersionMismatch


class _FakeProjectionService:
    def __init__(self) -> None:
        self.evolution_calls: list[tuple[object, object]] = []

    def control_console(self) -> dict[str, object]:
        return {
            "schemaVersion": "alphapilot_v63_1_projection_v1",
            "scope": "control-console",
            "stateVersion": "control:v1",
        }

    def evolution_pool(
        self,
        *,
        limit: int | str | None = None,
        cursor: str | None = None,
    ) -> dict[str, object]:
        self.evolution_calls.append((limit, cursor))
        return {
            "schemaVersion": "alphapilot_v63_1_projection_v1",
            "scope": "evolution-pool",
            "stateVersion": "evolution:v1",
            "collection": {
                "items": [{"runId": "run-2"}, {"runId": "run-1"}],
                "pageSize": 2,
                "nextCursor": "opaque-cursor",
                "hasMore": True,
                "stateVersion": "evolution:v1",
            },
        }

    def runtime_health(self) -> dict[str, object]:
        return {
            "schemaVersion": "alphapilot_v63_1_projection_v1",
            "scope": "runtime-health",
            "stateVersion": "runtime:v1",
            "status": "healthy",
        }


class _ConflictProjectionService(_FakeProjectionService):
    def evolution_pool(
        self,
        *,
        limit: int | str | None = None,
        cursor: str | None = None,
    ) -> dict[str, object]:
        raise StateVersionMismatch(
            ProjectionConflict(
                expectedStateVersion="evolution:old",
                actualStateVersion="evolution:new",
            )
        )


@contextmanager
def _service_context(service: object):
    yield service


class V631HttpRouterTests(unittest.TestCase):
    def test_feature_flag_defaults_to_disabled(self) -> None:
        router = V631HttpRouter(
            service_context=lambda: _service_context(_FakeProjectionService()),
            environ={},
        )

        self.assertIsNone(
            router.handle_get("/api/v63/projections/control-console", {})
        )

    def test_cursor_collection_contract_is_preserved(self) -> None:
        service = _FakeProjectionService()
        router = V631HttpRouter(
            service_context=lambda: _service_context(service),
            environ={"ALPHAPILOT_V63A_UI_ENABLED": "true"},
        )

        result = router.handle_get(
            "/api/v63/projections/evolution-pool",
            {"limit": ["2"], "cursor": ["cursor-1"]},
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.status, 200)
        self.assertEqual(service.evolution_calls, [("2", "cursor-1")])
        collection = result.payload["collection"]
        self.assertEqual(collection["nextCursor"], "opaque-cursor")
        self.assertIs(collection["hasMore"], True)

    def test_state_version_conflict_returns_refresh_discipline(self) -> None:
        router = V631HttpRouter(
            service_context=lambda: _service_context(_ConflictProjectionService()),
            environ={"ALPHAPILOT_V63A_UI_ENABLED": "true"},
        )

        result = router.handle_get(
            "/api/v63/projections/evolution-pool",
            {"cursor": ["stale"]},
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.status, 409)
        self.assertEqual(result.payload["error"], "state_version_mismatch")
        self.assertEqual(
            result.payload["message"],
            "底层状态已变更，请基于最新状态操作",
        )
        self.assertIs(result.payload["refreshRequired"], True)


class V631ProjectionHttpIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), ConsoleHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_disabled_projection_route_is_not_exposed(self) -> None:
        router = V631HttpRouter(
            service_context=lambda: _service_context(_FakeProjectionService()),
            environ={},
        )
        with patch.object(http_app, "_V63_ROUTER", router):
            with self.assertRaises(HTTPError) as raised:
                urlopen(
                    self.base_url + "/api/v63/projections/control-console",
                    timeout=2,
                )
        self.assertEqual(raised.exception.code, 404)

    def test_projection_route_and_once_heartbeat_stream(self) -> None:
        router = V631HttpRouter(
            service_context=lambda: _service_context(_FakeProjectionService()),
            environ={"ALPHAPILOT_V63A_UI_ENABLED": "true"},
        )
        with patch.object(http_app, "_V63_ROUTER", router):
            with urlopen(
                self.base_url + "/api/v63/projections/evolution-pool?limit=2",
                timeout=2,
            ) as response:
                payload = json.load(response)
            with urlopen(
                self.base_url + "/api/v63/events?once=1",
                timeout=2,
            ) as response:
                event_stream = response.read().decode("utf-8")

        self.assertEqual(payload["collection"]["pageSize"], 2)
        self.assertIn("event: heartbeat", event_stream)
        self.assertIn('"staleAfterSeconds":3', event_stream)
        self.assertIn('"connectionStatus":"connected"', event_stream)

    def test_v63_write_routes_are_always_read_only(self) -> None:
        router = V631HttpRouter(
            service_context=lambda: _service_context(_FakeProjectionService()),
            environ={"ALPHAPILOT_V63A_UI_ENABLED": "true"},
        )
        request = Request(
            self.base_url + "/api/v63/projections/evolution-pool",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with patch.object(http_app, "_V63_ROUTER", router):
            with self.assertRaises(HTTPError) as raised:
                urlopen(request, timeout=2)
            payload = json.loads(raised.exception.read().decode("utf-8"))

        self.assertEqual(raised.exception.code, 405)
        self.assertEqual(payload["error"], "v63_projection_api_read_only")


if __name__ == "__main__":
    unittest.main()
