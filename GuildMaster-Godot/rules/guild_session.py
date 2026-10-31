"""Transient application session: main-thread snapshots and asynchronous connections.

Kept outside Ren'Py's store. Game progress is never written to disk.
"""
import json
import os
import queue
import threading
import time
from collections import deque

PHASE_LABELS = {'draft': '开局轮抽', 'research': '情报收集', 'action': '公会行动',
                'final': '最终行动', 'finished': '终局结算'}

from guild_content import CARDS, CHARACTERS, HEROES, hero_selection, selectable_hero
from guild_engine import Engine
from guild_lobby import deal_characters, offer_hero


class Session:
    def __init__(self):
        self.engine = None
        self.server = None
        self.client = None
        self.game = None
        self.room = None
        self.rooms = []
        self.directory = False
        self.room_id = None
        self.room_password = ''
        self.pending_join = None
        self.player_id = 0
        self.role = "player"
        self.mode = "local"
        self.status = ""
        self.error = ""
        self.toast = ""
        self.toast_until = 0
        self.connecting = False
        self.events = queue.Queue()
        self.generation = 0
        self.last_revision = -1
        self.revision = 0
        self.resume = None
        self.address = ""
        self.share_host = ""
        self.connection_args = None
        self._lifecycle = threading.RLock()
        self.visual_events = deque(maxlen=200)
        self._log_cursor = None
        self.saves_dir_ref = None

    def notify(self, text):
        self.toast = str(text).replace("{", "(").replace("}", ")")
        self.toast_until = time.monotonic() + 5

    def close(self):
        # Publication and cancellation are serialized: a late connection must
        # never leave a listening room alive after the last UI tick.
        with self._lifecycle:
            self.generation += 1
            pending = [(self.server, self.client)]
            while True:
                try:
                    kind, _, data = self.events.get_nowait()
                except queue.Empty:
                    break
                if kind == "connected":
                    pending.append(data)
            self.client = self.server = self.engine = self.game = self.room = None
            self.connecting = False
            self.status = self.error = self.toast = ""
            self.resume = self.connection_args = None
            self.rooms = []
            self.directory = False
            self.room_id = self.pending_join = None
            self.room_password = ''
            self.visual_events.clear()
            self._log_cursor = None
        for server, client in pending:
            if client:
                client.close()
            if server:
                server.close()

    def _publish_connection(self, generation, server, client):
        with self._lifecycle:
            if generation == self.generation:
                self.events.put(("connected", generation, (server, client)))
                return
        client.close()
        if server:
            server.close()

    def local_lobby(self, name, options=None):
        from guild_modes import normalize_options
        self.close()
        self.mode, self.role, self.player_id = "local", "player", 0
        options=normalize_options(dict(options or {},solo=True),1)
        self.room = {"name": "离线单人挑战", "host_id": 0, "started": False,"drafting":False,
                     "spectators": 0, "allow_spectators": False, "max_players": 1,
                     "hero_offers": [],"options":options,
                     "players": [{"id": 0, "name": self.clean(name) or "公会长", "hero": 'bai_white',
                                  "hero_chosen": False, "bot": False, "ready": True, "connected": True}]}
        self.revision += 1

    @staticmethod
    def clean(text):
        return "".join(c for c in str(text) if c.isprintable() and c not in "{}[]")[:20].strip()

    def connect(self, name, address, port):
        self.close()
        try:
            port = int(port)
            if not 1 <= port <= 65535:
                raise ValueError()
            if not self.clean(name):
                raise ValueError("请先输入你的公会长昵称。")
            if not address.strip():
                raise ValueError('请输入服务器地址。')
        except (ValueError, TypeError) as exc:
            self.error = str(exc) or "端口应为 1–65535 之间的数字。"
            return
        self.mode, self.role = "network", "browser"
        self.player_id = None
        self.address = address.strip() + ":" + str(port)
        self.share_host = address.strip()
        self.connection_args = (self.clean(name), address.strip(), port)
        self.connecting = True
        self.status = "正在连接游戏服务器…"
        self._connect_worker()

    def _connect_worker(self):
        generation = self.generation
        name, address, port = self.connection_args
        def work():
            client = None
            try:
                from guild_network import Client
                client = Client(address, port, name, lobby=True)
                client.connect()
                self._publish_connection(generation, None, client)
            except Exception as exc:
                if client:
                    client.close()
                self.events.put(("error", generation, "连接失败：" + str(exc)))
        threading.Thread(target=work, name="guild-connect", daemon=True).start()

    def _acting_seat(self):
        """Offline seat following: whoever must act next owns the view and actions."""
        if not self.engine:
            return self.player_id if self.player_id is not None else 0
        game = self.engine.state
        pending = game.get('pending')
        if pending:
            return pending.get('player', 0)
        phase = game.get('phase')
        if phase == 'draft':
            for player in game['players']:
                if player.get('draft_choice') is None:
                    return player['id']
        elif phase == 'research':
            for player in game['players']:
                if not player.get('researched'):
                    return player['id']
        return game['players'][game.get('turn', 0)]['id']

    def _view(self):
        seat = self._acting_seat()
        self.game = self.engine.view(seat)
        self.game['view_player'] = seat
        self.capture_log_events()

    def saves(self):
        if not self.saves_dir_ref or not os.path.isdir(self.saves_dir_ref):
            return []
        result = []
        for name in os.listdir(self.saves_dir_ref):
            if not name.endswith('.json'):
                continue
            path = os.path.join(self.saves_dir_ref, name)
            try:
                with open(path, encoding='utf-8') as handle:
                    meta = json.loads(handle.readline())
                result.append((os.path.getmtime(path), dict(name=name, time=meta.get('saved_at', ''), seats=meta.get('seats', 1),
                                   round=meta.get('round', 1), phase=meta.get('phase', ''),
                                   title=meta.get('title', ''))))
            except (OSError, ValueError):
                continue
        result.sort(key=lambda item: item[0], reverse=True)
        return [entry for _, entry in result]

    def save_game(self, name=''):
        if not self.engine:
            raise ValueError('当前没有进行中的对局。')
        if not self.saves_dir_ref:
            raise ValueError('存档目录未配置。')
        os.makedirs(self.saves_dir_ref, exist_ok=True)
        seats = len(self.engine.state['players'])
        label = time.strftime('%Y-%m-%d %H:%M:%S')
        custom = ''.join(ch for ch in str(name or '').strip() if ch.isprintable() and ch not in '{}[]')[:32].strip()
        custom = ''.join('_' if ch in '<>:"/\\|?*' else ch for ch in custom).rstrip(' .')
        if not custom:
            custom = '存档'
        name = '%s %s' % (custom, time.strftime('%Y-%m-%d %H-%M-%S'))
        path = os.path.join(self.saves_dir_ref, name + '.json')
        index = 0
        while os.path.exists(path):
            index += 1
            path = os.path.join(self.saves_dir_ref, name + '-%d.json' % index)
        meta = dict(version=1, saved_at=label, title=custom, seats=seats,
                    round=self.engine.state.get('round', 1),
                    phase=PHASE_LABELS.get(self.engine.state.get('phase'), '进行中'),
                    players=[p['name'] for p in self.engine.state['players']])
        final = path + '.tmp'
        with open(final, 'w', encoding='utf-8') as handle:
            json.dump(meta, handle, ensure_ascii=False)
            handle.write('\n')
            json.dump(self.engine.export(), handle, ensure_ascii=False)
        os.replace(final, path)
        files = [n for n in os.listdir(self.saves_dir_ref) if n.endswith('.json')]
        if len(files) > 20:
            keep = {entry['name'] for entry in self.saves()[:20]}
            for name in files:
                if name not in keep:
                    os.remove(os.path.join(self.saves_dir_ref, name))
        self.notify('已存档：%s（第%s季 · %s）' % (os.path.basename(path)[:-5],
                    self.engine.state['round'], PHASE_LABELS.get(self.engine.state['phase'], '')))
        self.revision += 1
        return dict(name=os.path.basename(path), title=custom, seats=seats, round=self.engine.state['round'],
                    phase=PHASE_LABELS.get(self.engine.state.get('phase'), ''), saves=self.saves())

    def rename_players(self, names):
        """Offline hot-seat: every seat keeps its own nickname."""
        if not self.room:
            raise ValueError('当前没有房间。')
        if not isinstance(names, dict):
            raise ValueError('昵称格式不正确。')
        players = self.room.get('players', [])
        cleaned = {}
        for key, value in names.items():
            try:
                pid = int(key)
            except (TypeError, ValueError):
                continue
            if not any(int(p.get('id', -1)) == pid for p in players):
                continue
            clean = self.clean(value)
            if not clean:
                raise ValueError('昵称不能为空。')
            cleaned[pid] = clean
        if not cleaned:
            return
        for player in players:
            if int(player['id']) in cleaned:
                player['name'] = cleaned[int(player['id'])]
        if self.engine:
            for player in self.engine.state['players']:
                if int(player['id']) in cleaned:
                    player['name'] = cleaned[int(player['id'])]
            self._view()
        self.notify('已更新玩家昵称。')
        self.revision += 1

    def load_game(self, name):
        if not self.saves_dir_ref:
            raise ValueError('存档目录未配置。')
        if self.engine or (self.room and self.room.get('started')):
            raise ValueError('当前已有对局进行，先离开后再读取进度。')
        base = os.path.basename(str(name))
        if not base.endswith('.json'):
            raise ValueError('不认识的存档文件。')
        path = os.path.join(self.saves_dir_ref, base)
        if not os.path.isfile(path):
            raise ValueError('该存档已不存在。')
        with open(path, encoding='utf-8') as handle:
            json.loads(handle.readline())
            data = json.loads(handle.read())
        if not isinstance(data, dict) or data.get('version') != 1:
            raise ValueError('存档格式不正确。')
        engine_data = data.get('state')
        if not isinstance(engine_data, dict) or not isinstance(data.get('rules'), dict):
            raise ValueError('存档格式不正确。')
        players = [{"id": spec.get('id'), "name": spec.get('name'), "hero": spec.get('hero'),
                    "hero_chosen": True, "bot": False, "ready": True, "connected": True}
                   for spec in engine_data.get('players', [])]
        if not players:
            raise ValueError('存档中没有玩家资料。')
        self.close()
        self.mode, self.role, self.player_id = "local", "player", 0
        self.room = {"name": "离线单人挑战", "host_id": 0, "started": False, "drafting": False,
                     "spectators": 0, "allow_spectators": False,
                     "max_players": len(players), "hero_offers": [], "hero_offers_by_seat": {},
                     "selecting_seat": 0, "options": dict(data.get('rules').get('options', {})),
                     "players": players, "saves": self.saves()}
        self.engine = Engine.restore(data)
        self.room['started'] = True
        self._view()
        self.notify('已读取进度：%s' % base)
        self.revision += 1

    def lobby(self, kind, **args):
        if self.mode == "network":
            if kind in ('create_room', 'enter_room'):
                self.room_password = args.get('password', '')
                self.error = ''
            return self.send({"type": kind, **args})
        if not self.room or self.game:
            return
        players = self.room["players"]
        if kind == "set_guests":
            if self.room.get('started') or self.room.get('drafting'):
                raise ValueError('对局已开始，无法调整客座。')
            count = args.get('count')
            if type(count) is not int or not 0 <= count <= 4:
                raise ValueError('客座人数应为 0–4。')
            if len(players) - 1 == count:
                return
            while len(players) - 1 > count:
                players.pop()
            while len(players) - 1 < count:
                players.append({"id": len(players), "name": self.clean('客座%d' % len(players)) or ('客座%d' % len(players)),
                                "hero": 'bai_white', "hero_chosen": False, "bot": False, "ready": True, "connected": True})
            self.room['max_players'] = 1 + count
        elif kind=="set_options":
            if self.room.get('started'): raise ValueError('开局后不能修改规则。')
            from guild_modes import normalize_options
            seats = len(players) - 1
            self.room['options']=normalize_options(dict(args['options'],solo=(seats==0)),1+seats)
        elif kind == "set_hero":
            if not self.room.get('drafting'): raise ValueError('请先开始对局。')
            try:
                selected = (hero_selection(args.get("character"), args.get("variant"))
                            if "character" in args or "variant" in args else selectable_hero(args.get("hero")))
            except ValueError as exc:
                self.notify(str(exc))
                return
            seat = self.room.get('selecting_seat', 0)
            if HEROES[selected]['character'] not in self.room['hero_offers']:
                raise ValueError('只能从本次抽到的候选角色中选择。')
            players[seat]["hero"] = selected
            players[seat].update(hero_chosen=True, ready=True)
            next_seat = next((p['id'] for p in players if not p.get('hero_chosen')), None)
            if next_seat is None:
                from guild_modes import normalize_options
                options = normalize_options(dict(self.room['options'], solo=(len(players) == 1)), len(players))
                self.engine = Engine(players,options=options)
                self.room.update(started=True,drafting=False)
                self._view()
                seats = len(players) - 1
                self.notify("客座模式开始：%s 位客座玩家随你轮流操作。六轮内令文明与瘴气相邻；先选择起始手牌。" % seats if seats
                            else "单人挑战开始。六轮内令文明与瘴气相邻；先选择起始手牌。")
            else:
                self.room['selecting_seat'] = next_seat
                self.room['hero_offers'] = self.room['hero_offers_by_seat'][str(next_seat)]
        elif kind == "start":
            if self.room.get('started'): raise ValueError('对局已经开始。')
            offers = {}
            excluded = []
            for player in players:
                picks = deal_characters(excluded=excluded, count=self.room['options']['hero_draw'], options=self.room['options'])
                offers[str(player['id'])] = picks
                excluded = excluded + picks
            self.room.update(started=True,drafting=True,
                hero_offers_by_seat=offers,hero_offers=offers['0'],selecting_seat=0)
        self.revision += 1

    def send(self, message):
        try:
            if not self.client:
                raise ValueError("当前没有连接到房间。")
            self.client.send(message)
            self.error = ''
            return True
        except (OSError, ValueError, RuntimeError) as exc:
            self.notify(self.friendly_error(str(exc)))
            return False

    def action(self, kind, **args):
        if self.role == "spectator":
            self.notify("你正在观战，可以查看公开信息。")
            return False
        action = {"type": kind, **args}
        if self.mode == "network":
            return self.send({"type": "action", "action": action})
        if not self.engine:
            return False
        try:
            from guild_clock import advance
            advance(self.engine)
            self.engine.apply(self._acting_seat(), action)
            self._view()
            self.revision += 1
            return True
        except (ValueError, KeyError, TypeError) as exc:
            self.notify(str(exc))
            return False

    def tick(self):
        if self.mode == 'local' and self.engine:
            from guild_clock import advance
            if advance(self.engine):
                self._view()
                self.revision += 1
        if self.toast and time.monotonic() > self.toast_until:
            self.toast = ""
        while True:
            try:
                kind, generation, data = self.events.get_nowait()
            except queue.Empty:
                break
            if generation != self.generation:
                if kind == "connected":
                    if data[1]: data[1].close()
                    if data[0]: data[0].close()
                continue
            self.connecting = False
            if kind == "connected":
                self.server, self.client = data
                self.status = "已连接，正在同步房间…"
            elif kind == "error":
                self.error = data
                self.status = ""
            elif kind == "address":
                self.share_host = data[0]
                self.address = "%s:%s" % data
        if self.client:
            for msg in self.client.poll():
                kind = msg.get("type")
                if kind == 'server_welcome':
                    self.directory = True
                    self.connecting = False
                    self.status = self.error = ''
                    if self.pending_join:
                        self.send(self.pending_join)
                        self.pending_join = None
                elif kind == 'directory':
                    self.rooms = msg.get('rooms', [])
                    self.revision += 1
                elif kind == 'left_room':
                    self.visual_events.clear()
                    self._log_cursor = None
                    self.game = self.room = None
                    self.room_id = self.resume = None
                    self.player_id = None
                    self.role = 'browser'
                    self.error = ''
                    self.revision += 1
                elif kind == "welcome":
                    self.player_id = msg.get("player_id")
                    self.role = msg.get("role", self.role)
                    self.resume = msg.get("resume_token")
                    self.room_id = msg.get('room_id')
                elif kind == "snapshot":
                    self.room = msg.get("room")
                    self.game = msg.get("game")
                    self.capture_log_events()
                    self.status = ""
                    self.revision += 1
                elif kind == 'chat':
                    self.visual_events.append(('chat',self.friendly_error(msg.get('name','访客')+'：'+msg.get('message',''))))
                elif kind in ("error", "disconnected"):
                    # Preserve a specific rejection (password/full/etc.) when
                    # the socket closes immediately after that rejection.
                    if kind == "error" or not self.error:
                        self.error = self.friendly_error(msg.get("message", "与房间的连接已断开。"))
                    self.connecting = False
                    self.status = ""
                    self.status = ""
                    self.notify(self.error)

    def capture_log_events(self):
        if not self.game:
            self._log_cursor = None
            return
        latest = self.game.get('log_serial',0)
        if self._log_cursor is not None and latest >= self._log_cursor:
            for item in self.game.get('log',[]):
                if item.get('id',0) > self._log_cursor and not item.get('quiet'):
                    self.visual_events.append(('log',self.friendly_error(item['message'])))
        self._log_cursor = latest

    def needs_reconnect(self):
        return self.mode == 'network' and not self.connecting and (not self.client or not self.client.connected)

    def reconnect(self):
        if self.connecting:
            return
        if not self.connection_args:
            self.notify("请先连接服务器。")
            return
        if self.client:
            self.client.close()
        self.client = None
        self.generation += 1
        self.directory = False
        if self.room_id:
            self.pending_join = dict(type='enter_room', room_id=self.room_id,
                                     password=self.room_password, role=self.role,
                                     resume_token=self.resume or '')
        self.connecting = True
        self.error = ""
        self.status = "正在恢复房间席位…"
        self._connect_worker()

    def leave_room(self):
        if self.mode == 'local':
            self.close()
            return
        if self.client and self.client.connected:
            self.send(dict(type='leave_room'))
        else:
            self.game = self.room = None
            self.room_id = self.resume = self.pending_join = None
            self.reconnect()

    def can_free_action(self):
        return bool(self.game and self.game['phase'] not in ('finished','draft') and self.role == 'player'
                    and (self.mode == 'local' or (self.client and self.client.connected and not self.connecting)))

    def me(self):
        return next((p for p in (self.game or {}).get("players", []) if p["id"] == self.player_id), None)

    def can_act(self):
        if not self.game or self.role == "spectator" or self.game.get('pending'):
            return False
        if self.mode == "network" and (not self.client or not self.client.connected or
                                        self.connecting or (self.room or {}).get("paused")):
            return False
        return (self.game["phase"] in ("action", "final") and
                self.game["players"][self.game["turn"]]["id"] == self.player_id)

    def can_choose(self):
        pending = (self.game or {}).get('pending') or {}
        return (self.role != 'spectator' and pending.get('player') == self.player_id and
                (self.mode == 'local' or bool(self.client and self.client.connected and not self.connecting and not (self.room or {}).get('paused'))))

    @staticmethod
    def friendly_error(message):
        message = str(message).replace("{", "(").replace("}", ")")
        return {
            "Incorrect room password.": "房间密码不正确，请检查后重新加入。",
            "The room is full.": "玩家席位已满，可以尝试以观战身份加入。",
            "Spectators are not allowed in this room.": "房主尚未开放观战。",
            "The spectator seats are full.": "观战席位已满。",
            "The game has started. Join as a spectator or resume a player.": "对局已经开始，请选择观战或恢复原有席位。",
            "Client is not connected.": "连接已断开，请先尝试重连。",
            "Connection closed.": "与服务器的连接已断开，可重新连接恢复席位。",
            "Connection lost.": "网络连接中断，请尝试重连。",
            "Connection failed.": "连接失败，请检查服务器地址与端口。",
            "Only the host can do that.": "只有房主可以执行这个操作。",
            "Spectators are read-only.": "观战席只能查看公开信息。",
            "All players must be connected before starting.": "请等待所有玩家连接后再开始。",
            "All players must be ready before starting.": "请等待所有玩家准备好后再开始。",
            "Game paused: waiting for a disconnected player to reconnect.": "当前需要行动的玩家已断线，正在等待其重连。",
            "This player is already connected.": "这个席位已经在线。",
            "Invalid or expired resume token.": "原席位已无法恢复，请重新加入房间。",
            "Client send queue is full.": "网络繁忙，请稍后再试。",
        }.get(message, message)


session = Session()
