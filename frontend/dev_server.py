import os
import socket
import threading
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8001")
HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "8000"))


class ProxyHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def do_GET(self):
        if self.path.startswith("/api/") or self.path == "/api":
            self.proxy_request()
            return
        super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/") or self.path == "/api":
            self.proxy_request()
            return
        self.send_error(404)

    def proxy_request(self):
        target = f"{BACKEND_URL}{self.path.replace('/api', '', 1)}"
        parsed = urlparse(target)
        body = None
        headers = {}

        if self.headers.get("Content-Length"):
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length else b""

        for key, value in self.headers.items():
            if key.lower() not in {"host", "content-length"}:
                headers[key] = value

        req = urllib.request.Request(parsed.geturl(), data=body, headers=headers, method=self.command)

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                payload = response.read()
                self.send_response(response.status)
                for key, value in response.headers.items():
                    if key.lower() not in {"content-length", "transfer-encoding", "connection"}:
                        self.send_header(key, value)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()
                if payload:
                    self.wfile.write(payload)
        except Exception as exc:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(f'{{"error": "Proxy failed: {exc}"}}'.encode("utf-8"))

    def do_OPTIONS(self):
        if self.path.startswith("/api/") or self.path == "/api":
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            return
        self.send_error(404)

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    with ThreadingHTTPServer((HOST, PORT), ProxyHandler) as httpd:
        print(f"Serving frontend at http://{HOST}:{PORT}")
        print(f"Proxying /api -> {BACKEND_URL}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server")
