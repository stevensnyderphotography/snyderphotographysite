#!/usr/bin/env python3
"""Local-only helper for reorder.html. Runs on your computer; nothing is sent anywhere."""
import http.server, json, os, socketserver, subprocess, sys, threading, webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
PHOTOS = os.path.join(ROOT, 'photos')
EXTS = ('.jpg', '.jpeg', '.png', '.webp')

# Pick up any photos added or removed since the last run.
subprocess.run([sys.executable, os.path.join(ROOT, 'update-galleries.py')], cwd=ROOT)

def folders():
    return [d for d in sorted(os.listdir(PHOTOS))
            if os.path.isfile(os.path.join(PHOTOS, d, 'photos.json'))]

def images_in(folder):
    return sorted(f for f in os.listdir(os.path.join(PHOTOS, folder))
                  if f.lower().endswith(EXTS) and not f.startswith('.'))

def read_manifest(folder):
    with open(os.path.join(PHOTOS, folder, 'photos.json')) as fh:
        return json.load(fh)

def read_site():
    path = os.path.join(ROOT, 'site.json')
    return json.load(open(path)) if os.path.isfile(path) else {}

def apply_to_pages():
    subprocess.run([sys.executable, os.path.join(ROOT, 'update-galleries.py')], cwd=ROOT,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _host_ok(self):
        return self.headers.get('Host', '').split(':')[0] in ('localhost', '127.0.0.1')

    def do_GET(self):
        if not self._host_ok():
            return self._json({'error': 'bad host'}, 403)
        if self.path == '/api/galleries':
            out = []
            for f in folders():
                m = read_manifest(f)
                present = images_in(f)
                order = [x for x in m['order'] if x in present]
                hidden = [x for x in present if x not in order]
                tile = m.get('tile') if m.get('tile') in present else None
                hero = m.get('hero') if m.get('hero') in present else None
                out.append({'folder': f, 'alt': m.get('alt', ''), 'order': order,
                            'hidden': hidden, 'tile': tile, 'hero': hero})
            root = sorted(x for x in os.listdir(PHOTOS)
                          if x.lower().endswith(EXTS) and not x.startswith('.')
                          and os.path.isfile(os.path.join(PHOTOS, x)))
            return self._json({'galleries': out, 'root': root, 'home_hero': read_site().get('home_hero')})
        return super().do_GET()

    def do_POST(self):
        if not self._host_ok() or self.headers.get('X-Reorder') != '1':
            return self._json({'error': 'forbidden'}, 403)
        n = int(self.headers.get('Content-Length', 0))
        try:
            data = json.loads(self.rfile.read(n) or b'{}')
        except ValueError:
            return self._json({'error': 'bad json'}, 400)
        if self.path == '/api/save':
            folder, order = data.get('folder'), data.get('order')
            if folder not in folders() or not isinstance(order, list):
                return self._json({'error': 'unknown gallery'}, 400)
            present = images_in(folder)
            if len(set(order)) != len(order) or any(x not in present for x in order):
                return self._json({'error': 'list does not match the folder'}, 400)
            tile, hero = data.get('tile'), data.get('hero')
            if tile not in present or (hero is not None and hero not in present):
                return self._json({'error': 'tile or top image is not in the folder'}, 400)
            m = read_manifest(folder)
            m['order'] = order
            m['tile'] = tile
            m['hero'] = hero
            m['seen'] = sorted(set(m.get('seen', [])) | set(present))
            path = os.path.join(PHOTOS, folder, 'photos.json')
            with open(path, 'w') as fh:
                json.dump(m, fh, indent=2)
                fh.write('\n')
            apply_to_pages()
            return self._json({'ok': True, 'shown': len(order)})
        if self.path == '/api/home-hero':
            choice = data.get('path')
            allowed = set()
            for f in folders():
                allowed |= {f'photos/{f}/{x}' for x in images_in(f)}
            allowed |= {f'photos/{x}' for x in os.listdir(PHOTOS)
                        if x.lower().endswith(EXTS) and os.path.isfile(os.path.join(PHOTOS, x))}
            if choice not in allowed:
                return self._json({'error': 'photo not found'}, 400)
            site = read_site()
            site['home_hero'] = choice
            with open(os.path.join(ROOT, 'site.json'), 'w') as fh:
                json.dump(site, fh, indent=2)
                fh.write('\n')
            apply_to_pages()
            return self._json({'ok': True})
        if self.path == '/api/quit':
            self._json({'ok': True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        return self._json({'error': 'not found'}, 404)

class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

port = 8765
while True:
    try:
        srv = Server(('127.0.0.1', port), Handler)
        break
    except OSError:
        port += 1
        if port > 8800:
            sys.exit('Could not find a free port.')

url = f'http://localhost:{port}/reorder.html'
print(f'Reorder page: {url}')
print('Leave this window open while you work. Click "Done" on the page (or close this window) when finished.')
if not os.environ.get('NO_BROWSER'):
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
try:
    srv.serve_forever()
except KeyboardInterrupt:
    pass
print('Stopped.')
