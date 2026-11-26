"""
Dev server for prototypes/index_v2 on port 8081.
Serves files from the project root (so ../../ relative paths work),
but redirects bare / to /prototypes/index_v2/index.html.
"""
import http.server
import os

PORT = 8081
ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PATH = "/prototypes/index_v2/index.html"


class V2Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def do_GET(self):
        if self.path in ("/", ""):
            self.send_response(302)
            self.send_header("Location", DEFAULT_PATH)
            self.end_headers()
        else:
            super().do_GET()

    def log_message(self, fmt, *args):
        print(f"[8081] {self.address_string()} - {fmt % args}")


if __name__ == "__main__":
    with http.server.HTTPServer(("0.0.0.0", PORT), V2Handler) as httpd:
        print(f"Serving index_v2 on http://0.0.0.0:{PORT}")
        print(f"  Root  → {DEFAULT_PATH}")
        httpd.serve_forever()
