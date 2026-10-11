"""static server for the MONTAGE root (Range) + POST /frame?job=NAME&i=N (PNG/JPEG body -> cache/three_NAME/%05d.png|jpg). Port 8766."""
import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
import http.server, os, re, sys, urllib.parse
ROOT = XROOT + ''; CACHE = os.path.join(ROOT, 'cache')
class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=ROOT, **k)
    def log_message(self, *a): pass
    def end_headers(self): self.send_header('Access-Control-Allow-Origin', '*'); self.send_header('Cache-Control', 'no-store'); super().end_headers()
    def do_POST(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
        if u.path == '/frame':
            job = re.sub(r'[^A-Za-z0-9_]', '', q['job'][0]); i = int(q['i'][0]); ext = q.get('ext', ['png'])[0]; d = os.path.join(CACHE, 'three_' + job); os.makedirs(d, exist_ok=True)
            n = int(self.headers.get('Content-Length', 0)); open(os.path.join(d, f'{i:05d}.{ext}'), 'wb').write(self.rfile.read(n))
            self.send_response(200); self.end_headers(); self.wfile.write(b'ok'); return
        if u.path == '/done':
            job = re.sub(r'[^A-Za-z0-9_]', '', q['job'][0]); open(os.path.join(CACHE, 'three_' + job, 'DONE'), 'w').write('1'); self.send_response(200); self.end_headers(); self.wfile.write(b'ok'); return
        self.send_response(404); self.end_headers()
    def do_GET(self):   # Range support for mp3/mp4
        path = self.translate_path(urllib.parse.urlparse(self.path).path); rng = self.headers.get('Range')
        if rng and os.path.isfile(path):
            size = os.path.getsize(path); m = re.match(r'bytes=(\d*)-(\d*)', rng); a = int(m.group(1) or 0); b = int(m.group(2) or size - 1); b = min(b, size - 1)
            self.send_response(206); self.send_header('Content-Type', self.guess_type(path)); self.send_header('Content-Range', f'bytes {a}-{b}/{size}'); self.send_header('Content-Length', str(b - a + 1)); self.send_header('Accept-Ranges', 'bytes'); self.end_headers()
            with open(path, 'rb') as f: f.seek(a); self.wfile.write(f.read(b - a + 1))
            return
        super().do_GET()
if __name__ == '__main__':
    http.server.ThreadingHTTPServer(('127.0.0.1', int(sys.argv[1]) if len(sys.argv) > 1 else 8777), H).serve_forever()
