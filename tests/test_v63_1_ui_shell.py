from __future__ import annotations

import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen
from unittest.mock import patch

from alphapilot_control_console import http_app
from alphapilot_control_console.config import WEB_DIR
from alphapilot_control_console.http_app import ConsoleHandler
from alphapilot_control_console.v63_1_ui.http import V631HttpRouter


class V631UiShellStaticTests(unittest.TestCase):
    def test_shell_contains_connection_staleness_and_conflict_discipline(self) -> None:
        script = (Path(WEB_DIR) / "v63a.js").read_text(encoding="utf-8")

        self.assertIn("EventSource", script)
        self.assertIn("STALE_AFTER_MS = 3000", script)
        self.assertIn("底层状态已变更，请基于最新状态操作", script)
        self.assertIn("response.status === 409", script)
        self.assertIn("await refreshProjection()", script)
        self.assertIn("nextCursor", script)
        self.assertIn("hasMore", script)
        self.assertNotIn("while (page.hasMore)", script)

    def test_shell_has_bounded_page_replacement_not_unbounded_append(self) -> None:
        script = (Path(WEB_DIR) / "v63a.js").read_text(encoding="utf-8")

        self.assertIn("class CursorPager", script)
        self.assertIn("this.items = collection.items", script)
        self.assertNotIn("this.items.push(...collection.items)", script)

    def test_structured_current_pilot_has_human_readable_identity(self) -> None:
        script = (Path(WEB_DIR) / "v63a.js").read_text(encoding="utf-8")

        self.assertIn("function pilotIdentity(", script)
        self.assertIn('valueOf(pilot, ["campaignId"', script)
        self.assertNotIn(
            'valueOf(strategy, ["currentPilot"],',
            script,
        )

    def test_identity_only_candidate_explains_available_evidence(self) -> None:
        script = (Path(WEB_DIR) / "v63a.js").read_text(encoding="utf-8")

        self.assertIn('metric("Campaign"', script)
        self.assertIn('metric("Formal 角色"', script)
        self.assertIn('metric("证据状态"', script)
        self.assertIn("仅有候选身份与 Formal 角色", script)

    def test_stale_css_visibly_marks_realtime_values(self) -> None:
        stylesheet = (Path(WEB_DIR) / "v63a.css").read_text(encoding="utf-8")

        self.assertIn('[data-connection="stale"] [data-realtime]', stylesheet)
        self.assertIn("line-through", stylesheet)
        self.assertIn("数据陈旧", stylesheet)

    def test_mobile_headers_can_wrap_long_machine_statuses(self) -> None:
        stylesheet = (Path(WEB_DIR) / "v63a.css").read_text(encoding="utf-8")

        self.assertIn(".panel,\n  .panel-body", stylesheet)
        self.assertIn(".section-header {\n    align-items: flex-start;\n    flex-wrap: wrap;", stylesheet)
        self.assertIn(".section-header .status-badge", stylesheet)
        self.assertIn("white-space: normal", stylesheet)


class V631UiShellHttpTests(unittest.TestCase):
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

    def test_feature_flag_hides_v63_ui_shell(self) -> None:
        with patch.object(http_app, "_V63_ROUTER", V631HttpRouter(environ={})):
            with self.assertRaises(HTTPError) as raised:
                urlopen(self.base_url + "/v63a/control", timeout=2)

        self.assertEqual(raised.exception.code, 404)

    def test_feature_flag_serves_same_shell_for_all_v63_pages(self) -> None:
        router = V631HttpRouter(
            environ={"ALPHAPILOT_V63A_UI_ENABLED": "true"}
        )
        with patch.object(http_app, "_V63_ROUTER", router):
            paths = (
                "/v63a/control",
                "/v63a/strategy/example-id",
                "/v63a/evolution",
                "/v63a/demo",
                "/v63a/live",
            )
            for path in paths:
                with self.subTest(path=path):
                    with urlopen(self.base_url + path, timeout=2) as response:
                        body = response.read().decode("utf-8")
                    self.assertIn("AlphaPilot V63.1", body)
                    self.assertIn("/v63a.js", body)


if __name__ == "__main__":
    unittest.main()
