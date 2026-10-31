"""Matchmaking website: live status, group contact and project introduction.

Standard library only, mirroring ``guild_replay.ReplayWeb``: the game server
runs this next to the TCP lobby and the replay archive so one process publishes
the website, the replay viewer and the game itself.
"""
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

STATIC_FILES = {'/': 'index.html', '/index.html': 'index.html', '/style.css': 'style.css',
                '/app.js': 'app.js', '/favicon.svg': 'favicon.svg'}
STATIC_TYPES = {'html': 'text/html', 'css': 'text/css', 'js': 'text/javascript', 'svg': 'image/svg+xml'}
DEFAULT_CONFIG = {'name': '异世界公会长', 'version': '', 'tagline': '', 'server_host': '',
                  'game_port': 6677, 'replay_port': 6767, 'requirements': '', 'notice': ''}


class SiteWeb:
    """Serve the landing page; package downloads are retired."""

    def __init__(self, site_dir, download_dir=None, host='0.0.0.0', port=6680,
                 portrait_dir=None, overrides=None, status_provider=None):
        site = self
        self.site = Path(site_dir).resolve()
        self.download_dir = Path(download_dir).resolve() if download_dir else self.site / 'downloads'
        self.portraits = Path(portrait_dir).resolve() if portrait_dir else None
        self.config = self._read_config()
        self.status_provider = status_provider
        # Runtime settings (real ports, whether the replay site runs) win over site.json.
        for key, value in (overrides or {}).items():
            if value is not None:
                self.config[key] = value

        class Handler(BaseHTTPRequestHandler):
            head_only = False

            def do_HEAD(self):
                # Download managers and proxies probe files with HEAD; reuse the
                # GET routing but write headers only.
                self.head_only = True
                self.do_GET()

            def do_GET(self):
                path = urlsplit(self.path).path
                try:
                    if path == '/api/site':
                        payload = dict(site.config)
                        payload['downloads'] = site.downloads()
                        payload.update(downloads_enabled=False, download_message='加群2155021664下载')
                        self.reply(json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                                   'application/json; charset=utf-8')
                        return
                    if path == '/api/health':
                        self.json_reply({'online': True})
                        return
                    if path in ('/api/status', '/api/rooms'):
                        if site.status_provider is None:
                            self.json_reply({'online': True, 'rooms': []} if path.endswith('status') else [])
                        else:
                            status = site.status_provider()
                            self.json_reply(status if path.endswith('status') else status.get('rooms', []))
                        return
                    room_match = re.fullmatch(r'/api/rooms/([A-Fa-f0-9]{8})', path)
                    if room_match:
                        room = site.status_provider(room_match.group(1)) if site.status_provider else None
                        if room is None:
                            self.json_reply({'error': 'room_not_found'}, status=404)
                        else:
                            self.json_reply(room)
                        return
                    if path.startswith('/download/'):
                        site.send_download(self, unquote(path[len('/download/'):]))
                        return
                    if path.startswith('/shots/') and re.fullmatch(r'/shots/[A-Za-z0-9_.-]{1,64}\.(?:jpg|jpeg|png|webp)', path):
                        name = path.rsplit('/', 1)[1]
                        mime = 'image/png' if name.lower().endswith('.png') else 'image/webp' if name.lower().endswith('.webp') else 'image/jpeg'
                        self.reply((site.site / 'shots' / name).read_bytes(), mime, 'public, max-age=86400')
                        return
                    if path.startswith('/assets/hero/') and site.portraits and re.fullmatch(r'/assets/hero/[A-Za-z0-9_]{1,64}\.png', path):
                        self.reply((site.portraits / path.rsplit('/', 1)[1]).read_bytes(), 'image/png', 'public, max-age=86400')
                        return
                    name = STATIC_FILES.get(path)
                    if name:
                        content = (site.site / name).read_bytes()
                        self.reply(content, STATIC_TYPES[name.rsplit('.', 1)[1]] + '; charset=utf-8', 'no-store')
                        return
                    self.send_error(404)
                except (OSError, ValueError):
                    self.send_error(404)

            def json_reply(self, value, status=200):
                self.reply(json.dumps(value, ensure_ascii=False).encode('utf-8'),
                           'application/json; charset=utf-8', status=status, cors=True)

            def reply(self, content, mime, cache='no-store', status=200, cors=False):
                self.send_response(status)
                self.send_header('Content-Type', mime)
                self.send_header('Content-Length', str(len(content)))
                self.send_header('Cache-Control', cache)
                self.send_header('X-Content-Type-Options', 'nosniff')
                if cors:
                    self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'")
                self.end_headers()
                if not self.head_only:
                    self.wfile.write(content)

            def log_message(self, *args):
                pass

        self.http = ThreadingHTTPServer((host, port), Handler)
        self.port = self.http.server_port
        self.thread = None

    def _read_config(self):
        config = dict(DEFAULT_CONFIG)
        try:
            # utf-8-sig tolerates a BOM from Windows editors.
            config.update(json.loads((self.site / 'site.json').read_text(encoding='utf-8-sig')))
        except (OSError, ValueError):
            pass
        return config

    def downloads(self):
        """Package distribution has moved to the QQ group."""
        return []

    def send_download(self, handler, name):
        # Retired links, HEAD and Range requests must never serve local files.
        handler.reply('加群2155021664下载'.encode('utf-8'),
                      'text/plain; charset=utf-8', status=410)

    def start(self):
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        return self

    def close(self):
        if self.thread:
            self.http.shutdown()
            self.thread.join(timeout=5)
        self.http.server_close()
