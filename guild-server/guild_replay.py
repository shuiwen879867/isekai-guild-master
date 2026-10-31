"""Durable public-view replays and a read-only HTTP viewer (standard library)."""
import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
import guild_card_layouts as card_layouts
from guild_statistics import day_key, match_day, match_preview, win_statistics


def now():
    return datetime.now(timezone.utc).isoformat()


class ReplayStore:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self._summaries = {}
        self._metas = {}

    def _write(self, path, value):
        tmp = path.with_suffix('.tmp')
        with tmp.open('w', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=False, separators=(',', ':'))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)

    def start(self, room, engine):
        with self.lock:
            ident = uuid.uuid4().hex
            folder = self.root / ident
            folder.mkdir()
            meta = dict(id=ident, room=room, created=now(), updated=now(), status='进行中', count=0,
                        players=[dict(id=p['id'], name=p['name']) for p in engine.state['players']],
                        catalog=engine.replay_catalog())
            self._write(folder / 'meta.json', meta)
            self.append(ident, engine, '对局开始')
            return ident

    def append(self, ident, engine, label, player=None):
        with self.lock:
            folder = self.root / ident
            meta = json.loads((folder / 'meta.json').read_text(encoding='utf-8'))
            snapshot = engine.view(None, reveal=True)
            # The durable archive keeps every seat's hand, board and developments;
            # live spectators still use Engine.view(None) and never see them.
            self._write(folder / ('%08d.json' % meta['count']),
                        dict(index=meta['count'], time=now(), label=label, player=player, game=snapshot))
            meta.update(count=meta['count']+1, updated=now())
            if snapshot['phase']=='finished':
                meta['status']='已结束'
            self._write(folder / 'meta.json', meta)

    def finish(self, ident, status='已中断'):
        if not ident:
            return
        with self.lock:
            path = self.root / ident / 'meta.json'
            meta = json.loads(path.read_text(encoding='utf-8'))
            if meta['status']=='进行中':
                meta.update(status=status, updated=now())
                self._write(path,meta)

    def recover(self):
        # Previous process ended with unfinished sessions; rooms are never restored.
        for meta in self.list():
            self.finish(meta['id'])

    def list(self):
        with self.lock:
            result=[]
            for path in self.root.glob('*/meta.json'):
                try:
                    stamp=(path.stat().st_mtime_ns,path.stat().st_size)
                    cached=self._metas.get(path)
                    if cached and cached[0]==stamp:meta=dict(cached[1])
                    else:
                        meta=json.loads(path.read_text(encoding='utf-8'))
                        meta.pop('catalog',None)
                        self._metas[path]=(stamp,dict(meta))
                except (OSError, ValueError):
                    continue
                # The catalog is identical for every room; only send it on open.
                meta.pop('catalog',None)
                result.append(meta)
            return sorted(result,key=lambda m:m['created'],reverse=True)

    def summaries(self, date='all'):
        chosen=day_key(date)
        with self.lock:
            result=[]
            for meta in self.list():
                if chosen!='all' and match_day(meta.get('created'))!=chosen:continue
                ident=meta['id']
                if not re.fullmatch('[a-f0-9]{32}',ident) or not meta.get('count'):continue
                try:
                    path=self.root/ident/('%08d.json'%(meta['count']-1))
                    stamp=(meta['count'],meta.get('status'),meta.get('updated'),path.stat().st_mtime_ns)
                    cached=self._summaries.get(ident)
                    if cached and cached[0]==stamp:preview=cached[1]
                    else:
                        full=self.read(ident)
                        initial=self.read(ident,0)['game'];latest=self.read(ident,meta['count']-1)['game']
                        preview=match_preview(full,initial,latest)
                        self._summaries[ident]=(stamp,preview)
                    result.append(dict(meta,day=match_day(meta.get('created')),preview=preview))
                except (OSError,ValueError,KeyError,TypeError):continue
            return result

    def daily(self, date='today', limit=20, offset=0):
        chosen=day_key(date);matches=self.summaries(chosen)
        return dict(date=chosen,timezone='Asia/Shanghai',total=len(matches),
                    completed=sum(m['preview']['finished'] for m in matches),
                    ongoing=sum(m['status']=='进行中' for m in matches),
                    interrupted=sum(m['status']=='已中断' for m in matches),
                    limit=limit,offset=offset,matches=matches[offset:offset+limit])

    def statistics(self, date='all', players=None):
        chosen=day_key(date)
        return dict(win_statistics(self.summaries(chosen),players),date=chosen,timezone='Asia/Shanghai',players=players)

    def read(self, ident, step=None):
        if not re.fullmatch('[a-f0-9]{32}',ident):
            raise FileNotFoundError()
        with self.lock:
            path = self.root / ident / ('meta.json' if step is None else '%08d.json' % step)
            return json.loads(path.read_text(encoding='utf-8'))


class ReplayWeb:
    def __init__(self, store, host='0.0.0.0', port=6767):
        assets = Path(__file__).resolve().parent / 'replay_web'
        portraits = assets / 'portraits'
        cardthumbs = assets / 'cards'
        tiles = assets / 'tiles'
        pieces = Path(__file__).resolve().parent / 'images' / 'piece_png'
        cards = assets / 'cardfull'
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                path = urlsplit(self.path).path
                query = parse_qs(urlsplit(self.path).query)
                try:
                    if path=='/api/replays':
                        value=store.summaries(query.get('date',['all'])[0])
                    elif path=='/api/daily':
                        limit=int(query.get('limit',['20'])[0]);offset=int(query.get('offset',['0'])[0])
                        if not 1<=limit<=100 or offset<0:raise ValueError('Invalid pagination.')
                        value=store.daily(query.get('date',['today'])[0],limit,offset)
                    elif path=='/api/statistics':
                        players=int(query['players'][0]) if 'players' in query else None
                        if players is not None and players not in range(2,6):raise ValueError('Invalid player count.')
                        value=store.statistics(query.get('date',['all'])[0],players)
                    elif re.fullmatch('/api/replays/[a-f0-9]{32}(?:/steps/[0-9]{1,8})?',path):
                        parts=path.split('/')
                        value=store.read(parts[3],int(parts[5]) if len(parts)==6 else None)
                    elif re.fullmatch(r'/assets/portraits/[A-Za-z0-9_]{1,64}\.png',path):
                        self.reply((portraits/path.rsplit('/',1)[1]).read_bytes(),'image/png','public, max-age=86400')
                        return
                    elif re.fullmatch(r'/assets/cardthumbs/[0-9]{1,6}\.jpg',path):
                        self.card_asset(path,cardthumbs)
                        return
                    elif re.fullmatch(r'/assets/cards/[0-9]{1,6}\.jpg',path):
                        self.card_asset(path,cards)
                        return
                    elif re.fullmatch(r'/assets/piece/[0-9]{1,4}\.png',path):
                        name=path.rsplit('/',1)[1]
                        self.component_asset('images/piece_png/'+name,pieces/name,'image/png')
                        return
                    elif re.fullmatch(r'/assets/tiles/[A-Za-z0-9_-]{1,64}\.png',path):
                        import guild_content
                        name=path.rsplit('/',1)[1]
                        source=guild_content.TILES.get(name[:-4],{}).get('source')
                        self.component_asset(source,tiles/name,'image/png')
                        return
                    elif re.fullmatch(r'/assets/tokens/(?:adventurer|base)-[0-4]\.png',path):
                        self.reply((assets/'tokens'/path.rsplit('/',1)[1]).read_bytes(),'image/png','public, max-age=86400')
                        return
                    elif path in ('/','/index.html','/app.js','/style.css'):
                        name='index.html' if path=='/' else path[1:]
                        content=(assets/name).read_bytes()
                        mime={'html':'text/html','js':'text/javascript','css':'text/css'}[name.rsplit('.',1)[1]]
                        self.reply(content,mime+'; charset=utf-8')
                        return
                    else:
                        self.send_error(404)
                        return
                    self.reply(json.dumps(value,ensure_ascii=False).encode('utf-8'),'application/json; charset=utf-8')
                except ValueError:
                    self.send_error(400)
                except OSError:
                    self.send_error(404)

            def card_asset(self,path,folder):
                name=path.rsplit('/',1)[1]
                source=card_layouts.source_for_image(int(name[:-4]))
                self.component_asset(source,folder/name,'image/jpeg')

            def component_asset(self,source,fallback,mime):
                if source in card_layouts.LAYOUTS:
                    self.reply(card_layouts.render_svg(source),'image/svg+xml','public, max-age=86400')
                else:
                    self.reply(fallback.read_bytes(),mime,'public, max-age=86400')

            def reply(self,content,mime,cache='no-store'):
                self.send_response(200)
                self.send_header('Content-Type',mime)
                self.send_header('Content-Length',str(len(content)))
                self.send_header('Cache-Control',cache)
                self.send_header('X-Content-Type-Options','nosniff')
                self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'")
                self.end_headers()
                self.wfile.write(content)

            def log_message(self,*args):
                pass
        self.http=ThreadingHTTPServer((host,port),Handler)
        self.port=self.http.server_port
        self.thread=None

    def start(self):
        self.thread=threading.Thread(target=self.http.serve_forever,daemon=True)
        self.thread.start()
        return self

    def close(self):
        if self.thread:
            self.http.shutdown()
            self.thread.join(timeout=5)
        self.http.server_close()
