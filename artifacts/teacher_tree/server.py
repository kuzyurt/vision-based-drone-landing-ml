"""Local editor for the teacher branch tree.

Serves index.html and tree.json, and accepts PUT /tree.json to write edits
back to disk (keeping one .bak copy of the previous version).

    python artifacts/teacher_tree/server.py [--port 8765]

Everything is bound to 127.0.0.1. Nothing is served to the network.
"""
from __future__ import annotations

import argparse
import json
import shutil
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
INDEX = HERE / "index.html"
TREE = HERE / "tree.json"
BACKUP = HERE / "tree.bak.json"
MAX_BODY = 8 * 1024 * 1024


class Handler(BaseHTTPRequestHandler):
    server_version = "TeacherTree/1.0"

    def log_message(self, fmt, *args):  # keep the console quiet
        return

    def _send(self, status: int, body: bytes, ctype: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._send(200, INDEX.read_bytes(), "text/html; charset=utf-8")
        elif path == "/tree.json":
            if not TREE.exists():
                self._send(404, b'{"error":"tree.json missing"}', "application/json")
                return
            self._send(200, TREE.read_bytes(), "application/json; charset=utf-8")
        else:
            self._send(404, b"not found", "text/plain; charset=utf-8")

    def do_PUT(self):
        path = self.path.split("?", 1)[0]
        if path != "/tree.json":
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_BODY:
            self._send(413, b'{"error":"body size"}', "application/json")
            return
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as err:
            self._send(400, json.dumps({"error": f"invalid JSON: {err}"}).encode(), "application/json")
            return
        if not isinstance(data, dict) or not isinstance(data.get("roots"), list):
            self._send(400, b'{"error":"expected an object with a roots array"}', "application/json")
            return

        tmp = TREE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if TREE.exists():
            shutil.copyfile(TREE, BACKUP)
        tmp.replace(TREE)

        body = json.dumps({"ok": True, "bytes": TREE.stat().st_size}).encode()
        self._send(200, body, "application/json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    if not INDEX.exists() or not TREE.exists():
        raise SystemExit(f"missing files in {HERE}: index.html and tree.json are required")

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"teacher tree editor: http://{args.host}:{args.port}/", flush=True)
    print(f"editing: {TREE}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
