import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


class LocalApiServer:
    def __init__(self) -> None:
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/delay"):
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            delay_ms = int(query.get("delayMs", ["0"])[0] or 0)
            branch = str(query.get("branch", [""])[0] or "")
            if delay_ms > 0:
                time.sleep(delay_ms / 1000)
            self._write_json({"ok": True, "branch": branch, "delayMs": delay_ms, "path": parsed.path})
            return
        if self.path.startswith("/text/"):
            self._write_text(f"API_REAL: GET {self.path}")
            return
        self._write_json({"ok": True, "method": "GET", "path": self.path})

    def do_POST(self) -> None:  # noqa: N802
        raw_body = self.rfile.read(int(self.headers.get("Content-Length", "0") or "0"))
        if self.path.startswith("/text/"):
            self._write_text(f"API_REAL: POST {self.path}")
            return
        self._write_json(
            {
                "ok": True,
                "method": "POST",
                "path": self.path,
                "token": self.headers.get("X-Test-Token"),
                "body": json.loads(raw_body.decode("utf-8")) if raw_body else None,
            }
        )

    def _write_json(self, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _write_text(self, payload: str) -> None:
        body = payload.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        return None
