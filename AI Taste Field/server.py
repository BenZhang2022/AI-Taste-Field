from http.server import HTTPServer, SimpleHTTPRequestHandler
from functools import partial
import sys

class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

port = 8000
handler = partial(CORSRequestHandler, directory='.')
httpd = HTTPServer(('localhost', port), handler)
print(f"Serving at http://localhost:{port}")
httpd.serve_forever() 