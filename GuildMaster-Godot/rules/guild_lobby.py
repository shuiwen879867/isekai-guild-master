"""One public TCP endpoint, many authoritative rooms. No Ren'Py dependency."""
import random
import logging
import secrets
import time

from guild_content import CHARACTERS, HEROES, hero_selection, selectable_hero
from guild_network import (RoomServer, CLIENT_VERSION, NETWORK_PROTOCOL,
                           _safe_text, _string)

_LOGGER = logging.getLogger(__name__)


def deal_characters(excluded=(), count=2, options=None):
    pool = [key for key, data in CHARACTERS.items() if key not in excluded
            and any(HEROES.get(h, {}).get('available', False) for h in data['variants'].values())]
    if len(pool) < count:
        raise ValueError('没有足够的角色可供抽选。')
    return random.SystemRandom().sample(pool, count)


def offer_hero(offers):
    return next(h for h in CHARACTERS[offers[0]]['variants'].values()
                if HEROES[h].get('available', False))


class HostedRoom(RoomServer):
    """Reuse room rules, but all socket ownership belongs to LobbyServer."""
    def __init__(self, hub, room_id, banned_characters=None, options=None, **kwargs):
        super().__init__(**kwargs)
        from guild_modes import normalize_options
        self.options = normalize_options(options)
        self.drafting = False
        self._draft_seed = None
        banned = [] if banned_characters is None else banned_characters
        if not isinstance(banned,list) or any(not isinstance(k,str) or k not in CHARACTERS for k in banned):
            raise ValueError('禁用角色列表不正确。')
        self.banned_characters = sorted(set(banned))
        allowed = [k for k,c in CHARACTERS.items() if k not in banned
                   and any(HEROES[h].get('available') for h in c['variants'].values())]
        if len(allowed) < self.max_players * self.options["hero_draw"]:
            raise ValueError('剩余角色不足：%s人房间至少需要%s名角色，请减少禁用或房间人数。' % (self.max_players,self.max_players*self.options["hero_draw"]))
        self.hub, self.room_id = hub, room_id
        self.offers = {}
        self.kicked_names = set()
        self.replay_id = None
        self.touched = time.monotonic()
        self.created_at = time.time()
        self.started_at = None
        self.empty_since = None
        self._disconnect_deadlines = {}

    def _send(self, peer, message):
        if message.get('type') == 'welcome':
            message = dict(message, room_id=self.room_id)
        self.hub._send(peer, message)

    def _error(self, peer, message, fatal=False):
        # Rejected room entry must not disconnect the server browser.
        self.hub._error(peer, message, fatal=False)

    def _drop(self, peer):
        self.hub._drop(peer)

    def enter(self, peer, message, owner=False):
        if peer.name.casefold() in self.kicked_names:
            raise ValueError('你已被房主移出此房间。')
        if message.get('role', 'player') == 'player' and not message.get('resume_token'):
            name = _safe_text(peer.name, 32)
            existing = next((p for p in self._players.values()
                             if p['name'].casefold() == name.casefold()), None)
            if existing:
                if existing['id'] in self._player_peers:
                    raise ValueError('此昵称的玩家已经在线，不能接管其席位。')
                # Explicit product rule: an offline same-name seat can resume.
                # Room password is still checked by the normal join path.
                token = next(k for k, v in self._resume_tokens.items() if v == existing['id'])
                message = dict(message, resume_token=token)
        if self.drafting and message.get('role','player')=='player' and not message.get('resume_token'):
            raise ValueError('对局已开始选角，请观战或恢复原有席位。')
        before = set(self._players)
        self._next_id = next((i for i in range(5) if i not in self._players),5)
        super()._join(peer, dict(message, type='join', name=peer.name,
                                host_token=self.host_token if owner else ''))
        peer.room_id = self.room_id
        self._peers[peer.sock] = peer
        for pid in set(self._players) - before:
            self._players[pid].update(hero='bai_white',hero_chosen=False)
        if peer.role == 'player' and self._engine is not None:
            self._engine._player(peer.player_id)['connected'] = True
            self._disconnect_deadlines.pop(peer.player_id, None)
        if peer.role == 'player':
            self.empty_since = None
        self.touched = time.monotonic()
        _LOGGER.info('Room %s: %s entered as %s', self.room_id, peer.name, peer.role)

    def detach(self, peer):
        self._peers.pop(peer.sock, None)
        if self._player_peers.get(peer.player_id) is peer:
            self._player_peers.pop(peer.player_id)
            self._players[peer.player_id]['connected'] = False
            if self._engine is not None:
                self._engine._player(peer.player_id)['connected'] = False
            if self._engine is None:
                self._players[peer.player_id]['ready'] = False
            _LOGGER.info('Room %s: player %s disconnected', self.room_id,
                         self._players[peer.player_id]['name'])
        if not self._player_peers and self.empty_since is None:
            self.empty_since = time.monotonic()
        self.touched = time.monotonic()
        self._dirty = True

    def _command(self, peer, message):
        kind = message.get('type')
        try:
            self._maintenance()
            before_engine = self._engine
            before_state = self._engine.state if self._engine else None
            if 'player_id' in message:
                raise ValueError('Player identity is assigned by the server.')
            if kind == 'action' and not isinstance(message.get('action'), dict):
                raise ValueError('行动必须是一个对象。')
            if kind == 'end_session':
                raise ValueError('房间由服务器托管；离开不会结束其他玩家的对局。')
            if kind == 'kick':
                target = message.get('target_id')
                if peer.role != 'player' or peer.player_id != self._host_id:
                    raise ValueError('只有房主可以踢出玩家。')
                if type(target) is not int or target not in self._players or target == self._host_id:
                    raise ValueError('请选择另一位玩家。')
                self.kicked_names.add(self._players[target]['name'].casefold())
                victim = self._player_peers.get(target)
                if victim:
                    self._send(victim,dict(type='error',message='你已被房主移出房间。'))
                    self.hub._leave(victim)
                self._resume_tokens = {k:v for k,v in self._resume_tokens.items() if v!=target}
                if self._engine:
                    self._engine._player(target)['withdrawn'] = True
                    self._engine._undo_checkpoint = None
                    self._players[target]['withdrawn'] = True
                else:
                    self._players.pop(target)
                    self.offers.pop(target,None)
                    self._finish_draft()
            elif kind == 'start':
                from guild_modes import normalize_options
                if peer.role!='player' or peer.player_id!=self._host_id:
                    raise ValueError('只有房主可以开始对局。')
                if self._engine or self.drafting:
                    raise ValueError('对局已经开始。')
                if not all(p['connected'] and p['ready'] for p in self._players.values()):
                    raise ValueError('请等待所有玩家连接并准备。')
                self.options=normalize_options(self.options,len(self._players))
                seed=message.get('seed')
                if seed is not None and type(seed) is not int: raise ValueError('随机种子必须是整数。')
                offers={}
                for pid in self._players:
                    excluded=self.banned_characters+[c for pair in offers.values() for c in pair]
                    offers[pid]=deal_characters(excluded,self.options['hero_draw'],self.options)
                self.offers=offers;self.drafting=True;self._draft_seed=seed
                _LOGGER.info('Room %s: draft started with %s player(s)', self.room_id, len(self._players))
                for pid,p in self._players.items(): p.update(hero=offer_hero(offers[pid]),hero_chosen=False)
            elif kind == 'set_hero':
                if peer.role != 'player' or self._engine is not None or not self.drafting:
                    raise ValueError('请在房主开始对局并发出候选角色后选择。')
                hero = (hero_selection(message.get('character'), message.get('variant'))
                        if 'character' in message else selectable_hero(message.get('hero')))
                if HEROES[hero]['character'] not in self.offers.get(peer.player_id, []):
                    raise ValueError('只能从本次抽到的候选角色中选择。')
                self._players[peer.player_id].update(hero=hero, hero_chosen=True)
                if all(p.get('hero_chosen') for p in self._players.values()):
                    self._finish_draft()
            elif kind=='ready' and self.drafting:
                raise ValueError('对局已开始，请完成角色选择。')
            elif kind=='set_options':
                if peer.player_id!=self._host_id or self.drafting or self._engine:
                    raise ValueError('只有房主能在开局前修改设置。')
                from guild_modes import normalize_options
                options=normalize_options(message.get('options'))
                allowed=len(CHARACTERS)-len(self.banned_characters)
                if allowed<self.max_players*options['hero_draw']: raise ValueError('候选张数超过角色池容量。')
                self.options=options
                for p in self._players.values():p['ready']=False
            elif kind == 'action' and message.get('action', {}).get('type') in ('sell_event', 'discard_achievement','sell_gem'):
                if peer.role != 'player' or self._engine is None:
                    raise ValueError('当前不能售卖卡牌。')
                self._engine.apply(peer.player_id, message['action'])
            else:
                super()._command(peer, message)
            recorder = self.hub.replay_store
            if recorder:
                if self._engine is not None and before_engine is None:
                    self.replay_id = recorder.start(self.room_name,self._engine)
                elif self._engine is not None and self._engine.state is not before_state:
                    previous_serial = before_state.get('log_serial',0)
                    messages = [e['message'] for e in self._engine.state['log'] if e.get('id',0)>previous_serial]
                    label = ' / '.join(messages) or ('%s完成一个选择步骤' % peer.name)
                    recorder.append(self.replay_id,self._engine,label,peer.player_id)
                elif before_engine is not None and self._engine is None:
                    recorder.finish(self.replay_id,'已结束')
            if kind == 'return_lobby' and before_engine is not None and self._engine is None and peer.player_id == self._host_id:
                self.offers = {};self.drafting=False;self.started_at=None;self._disconnect_deadlines.clear()
                for player in self._players.values():
                    player.update(hero='bai_white',hero_chosen=False,ready=False)
            self.touched = time.monotonic()
            self._dirty = True
            if kind == 'action':
                _LOGGER.info('Room %s: player %s action %s', self.room_id, peer.name,
                             message.get('action', {}).get('type', 'unknown'))
        except (ValueError, TypeError, KeyError) as exc:
            self._error(peer, str(exc))

    def _finish_draft(self):
        if self.drafting and self._players and all(p.get('hero_chosen') for p in self._players.values()):
            from guild_engine import Engine
            from guild_clock import sync
            self._engine = Engine(list(self._players.values()),seed=self._draft_seed,options=self.options)
            for pid, player in self._players.items():
                self._engine._player(pid)['connected'] = player.get('connected', False)
            sync(self._engine)
            self.drafting = False
            self.started_at = time.time()
            _LOGGER.info('Room %s: match started (%s)', self.room_id, self.room_name)

    def _maintenance(self):
        if self._engine:
            from guild_clock import advance, close_for_round
            def record(pid):
                if self.hub.replay_store and self.replay_id:
                    self.hub.replay_store.append(self.replay_id,self._engine,'自动完成超时步骤',pid)
            changed = advance(self._engine,on_step=record)
            now = time.monotonic()
            waiting = set(self._pause_info()[1])
            for pid in list(self._disconnect_deadlines):
                if pid not in waiting:
                    self._disconnect_deadlines.pop(pid, None)
            grace = self.options.get('disconnect_seconds', 30)
            for pid in waiting:
                self._disconnect_deadlines.setdefault(pid, now + grace)
            expired = next((pid for pid, deadline in self._disconnect_deadlines.items()
                            if pid in waiting and now >= deadline), None)
            if expired is not None:
                self._disconnect_deadlines.pop(expired, None)
                name = self._players.get(expired, {}).get('name', str(expired))
                _LOGGER.info('Room %s: player %s reconnect grace expired', self.room_id, name)
                close_for_round(self._engine, expired, '断线超过%s秒' % grace,
                                now=now, on_step=record)
                changed = True
            if changed:
                self._dirty = self.hub._dirty = True

    def _room_view(self):
        view = super()._room_view()
        now = time.monotonic()
        remaining = {str(pid): max(0, int(deadline-now+0.999))
                     for pid, deadline in self._disconnect_deadlines.items()}
        view.update(started=self.drafting or self._engine is not None,
                    drafting=self.drafting, options=self.options,
                    disconnect_remaining=remaining)
        return view

    def _broadcast_snapshots(self):
        room = dict(self._room_view(), id=self.room_id, banned_characters=self.banned_characters)
        for peer in list(self._peers.values()):
            if peer.closing_at is not None:
                continue
            try:
                private_room = dict(room, hero_offers=list(self.offers.get(peer.player_id, [])))
                private_room['players'] = [dict(p, hero=p['hero'] if p['id']==peer.player_id or p.get('hero_chosen') else None)
                                           for p in room['players']]
                game = self._engine.view(peer.player_id) if self._engine else None
                self._send(peer, dict(type='snapshot', room=private_room, game=game))
            except Exception:
                logging.exception('Room snapshot failed')
                self._error(peer, '房间同步失败，请重新连接。')


class LobbyServer(RoomServer):
    def __init__(self, host='0.0.0.0', port=6677, max_rooms=32, idle_hours=24, replay_store=None):
        super().__init__(host=host, port=port)
        if max_rooms < 1 or idle_hours <= 0:
            raise ValueError('max_rooms and idle_hours must be positive.')
        self.rooms = {}
        self.replay_store = replay_store
        self.max_rooms = max_rooms
        self.started_at = time.time()
        # idle_hours is accepted only for old launch commands; never retains rooms.

    def _maintenance(self):
        for room in list(self.rooms.values()):
            room._maintenance()
        self._prune()

    def _prune(self):
        now = time.monotonic()
        for rid, room in list(self.rooms.items()):
            if room._player_peers:
                room.empty_since = None
            else:
                # Running matches survive long enough for every seat to use the
                # configured reconnect grace. Empty, unstarted lobbies do not.
                if room._engine is not None:
                    if room.empty_since is None:
                        room.empty_since = now
                    if now-room.empty_since < room.options.get('disconnect_seconds', 30):
                        continue
                if self.replay_store:
                    self.replay_store.finish(room.replay_id)
                del self.rooms[rid]
                # Spectators cannot keep an abandoned game alive. Remove the room
                # before returning them to the directory, avoiding recursive prune.
                for peer in list(room._peers.values()):
                    self._leave(peer)
                    self._send(peer, dict(type='notice', message='房间已销毁：所有玩家已离开或重连宽限已结束。'))
                room._peers.clear()
                self._dirty = True
                _LOGGER.info('Room %s destroyed after becoming empty', rid)

    def public_status(self, room_id=None):
        """Return the privacy-limited, JSON-ready robot status document."""
        now = time.time()
        rooms = []
        for rid, room in list(self.rooms.items()):
            engine = room._engine
            if engine is None or engine.state.get('phase') == 'finished':
                continue
            state = engine.state
            players = [dict(id=p['id'], name=p['name'], hero=p.get('hero'),
                            connected=bool(room._players.get(p['id'], {}).get('connected')),
                            closed=bool(p.get('passed')), withdrawn=bool(p.get('withdrawn')))
                       for p in state.get('players', [])]
            active_players = [p for p in players if not p['withdrawn']]
            started = room.started_at or room.created_at
            rooms.append(dict(id=rid, name=room.room_name,
                              started_at=datetime_utc(started),
                              duration_seconds=max(0, int(now-started)),
                              phase=state.get('phase'), round=state.get('round'),
                              season=state.get('season'), civilization=state.get('civ'),
                              miasma=state.get('miasma'), map_type=room.options.get('map_type'),
                              player_count=len(active_players), seat_count=len(players),
                              online_player_count=sum(p['connected'] for p in active_players),
                              players=players))
        if room_id is not None:
            wanted = str(room_id).upper()
            return next((room for room in rooms if room['id'] == wanted), None)
        names = [p['name'] for room in rooms for p in room['players'] if not p['withdrawn']]
        connected_people = sum(peer.joined and peer.closing_at is None
                               for peer in list(self._peers.values()))
        return dict(online=True, server_started_at=datetime_utc(self.started_at),
                    uptime_seconds=max(0, int(now-self.started_at)),
                    connected_people=connected_people,
                    active_room_count=len(rooms), active_player_count=len(names),
                    active_online_player_count=sum(room['online_player_count'] for room in rooms),
                    players=names, rooms=rooms)

    def _directory(self, peer):
        entries = []
        for rid, room in self.rooms.items():
            view = room._room_view()
            own = next((p for p in room._players.values()
                        if p['name'].casefold() == peer.name.casefold()), None)
            entries.append(dict(id=rid, name=room.room_name, locked=bool(room.password),
                                players=len(room._players), online=len(room._player_peers),
                                max_players=room.max_players, started=view['started'],
                                spectators=view['spectators'], allow_spectators=room.allow_spectators,
                                banned_characters=room.banned_characters,
                                resumable=bool(own and not own['connected'])))
        self._send(peer, dict(type='directory', rooms=entries))

    def _leave(self, peer):
        room = self.rooms.get(getattr(peer, 'room_id', None))
        if room:
            room.detach(peer)
            self._prune()
        peer.room_id = None
        peer.player_id = None
        peer.role = 'browser'
        self._send(peer, dict(type='left_room'))
        self._dirty = True

    def _drop(self, peer):
        room = self.rooms.get(getattr(peer, 'room_id', None))
        if room:
            room.detach(peer)
            self._prune()
        peer.joined = False  # The transport must not touch legacy single-room seats.
        super()._drop(peer)
        self._dirty = True

    def _command(self, peer, message):
        try:
            kind = message.get('type')
            if not peer.joined:
                if kind != 'hello':
                    raise ValueError('过期的客户端，请更新')
                if (message.get('client_version') != CLIENT_VERSION or
                        message.get('protocol') != NETWORK_PROTOCOL):
                    raise ValueError('过期的客户端，请更新')
                peer.name = _safe_text(_string(message.get('name', ''), 'name', 128), 32)
                if not peer.name:
                    raise ValueError('请输入昵称。')
                peer.joined, peer.role, peer.room_id = True, 'browser', None
                _LOGGER.info('Client connected: %s', peer.name)
                self._send(peer, dict(type='server_welcome', name=peer.name,
                                      protocol=NETWORK_PROTOCOL, version=CLIENT_VERSION))
                self._prune()
                self._directory(peer)
                return
            if kind == 'leave_room':
                self._leave(peer)
                return
            if kind == 'list_rooms':
                self._prune()
                self._directory(peer)
                return
            room = self.rooms.get(getattr(peer, 'room_id', None))
            if room:
                room._command(peer, message)
            elif kind == 'create_room':
                self._prune()
                if len(self.rooms) >= self.max_rooms:
                    raise ValueError('服务器房间已满，请稍后再试。')
                rid = secrets.token_hex(4).upper()
                while rid in self.rooms:
                    rid = secrets.token_hex(4).upper()
                room = HostedRoom(self, rid,
                    room_name=_safe_text(message.get('room_name', ''), 32, '旅人的公会'),
                    password=_string(message.get('password', ''), 'password', 256),
                    allow_spectators=message.get('allow_spectators', True),
                    banned_characters=message.get('banned_characters',[]),
                    options=message.get('options'),
                    max_players=message.get('max_players', 4))
                room.enter(peer, dict(role='player', password=room.password), owner=True)
                self.rooms[rid] = room
                _LOGGER.info('Room %s created by %s (%s)', rid, peer.name, room.room_name)
            elif kind == 'enter_room':
                rid = _string(message.get('room_id', ''), 'room id', 32)
                room = self.rooms.get(rid)
                if room is None:
                    self._send(peer, dict(type='left_room'))
                    self._directory(peer)
                    raise ValueError('房间已销毁：断线宽限已结束，请创建或选择其他房间。')
                room.enter(peer, message)
            else:
                raise ValueError('请先选择房间。')
            self._dirty = True
        except (ValueError, TypeError, KeyError) as exc:
            self._error(peer, str(exc), fatal=not peer.joined)
        except Exception:
            logging.exception('Lobby command failed')
            self._error(peer, '服务器无法处理这个请求。', fatal=not peer.joined)

    def _broadcast_snapshots(self):
        for room in list(self.rooms.values()):
            if room._dirty:
                room._dirty = False
                room._broadcast_snapshots()
        for peer in list(self._peers.values()):
            if peer.joined and not getattr(peer, 'room_id', None):
                self._directory(peer)


def datetime_utc(timestamp):
    from datetime import datetime, timezone
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat().replace('+00:00', 'Z')
