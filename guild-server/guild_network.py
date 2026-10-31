"""Standalone, standard-library TCP rooms for guild_engine.Engine.

    server = RoomServer(port=0).start()
    host = Client('127.0.0.1', server.port, 'Host',
                  host_token=server.host_token).connect()
    guest = Client('127.0.0.1', server.port, 'Guest').connect()

Client construction does no I/O. connect() opens TCP (up to five seconds, so
call it in a UI worker); the join handshake and subsequent I/O run in a daemon
thread. send(dict) queues a command without waiting for the server. poll()
drains received dictionaries, including errors and a final disconnected event.
Close both clients and the server when leaving the room. Instances are single
use; reconnect with a new Client and the welcome's resume_token.

Every message is a UTF-8 JSON object preceded by a four-byte unsigned big-endian
payload length, 1..262144 bytes. The first client message is type='join' with
name, role, password, host_token and resume_token. Only the server's local
host_token can claim host authority; arriving first alone grants no privileges.
For the public lobby endpoint, the first message is type='hello' and includes
client_version and protocol. The lobby rejects incompatible clients before
showing the room directory.

Commands: set_hero(hero), ready(ready=True), start(seed=None), chat(message),
action(action={...}), return_lobby(), end_session().
The command name is the 'type' field. Omitted heroes default to 'bai_white'.
Every human must be ready before starting, including the host. Spectators may
chat but cannot change the lobby or game. Commands always use the authenticated
connection's identity. start, return_lobby and end_session are host-only.
return_lobby is allowed after a finished game; end_session closes the room.

Messages: welcome(player_id, role, resume_token, is_host), error(message),
chat(player_id, name, role, message), snapshot(room, game), disconnected(message).
room contains name, host_id, players, spectators (count), started,
allow_spectators, max_players, paused, waiting_for (disconnected pending player
IDs), and chat (latest 50 chat messages). Each player has id, name, hero,
bot (always False), ready, connected. game is None in the lobby, otherwise
Engine.view(own_id), or Engine.view(None) for spectators. Tokens never appear
in snapshots. The Client also exposes player_id, resume_token and connected.

Disconnects keep the player's seat in both lobby and game; a valid resume
token reclaims it and host authority, if any. Lobby disconnects reset ready.
There is no AI or automatic gameplay. Action/final phases pause when the current
actor is disconnected. In research, connected players can submit their pending
choices; paused becomes True when only disconnected pending players remain.
Starting requires every reserved seat to be connected and ready.

This protocol provides room access control, not transport encryption. Use it
on a trusted LAN or inside an encrypted tunnel when tokens must stay private.
"""

import collections
import hmac
import json
import logging
import queue
import secrets
import selectors
import socket
import struct
import threading
import time
import unicodedata


MAX_FRAME_SIZE = 256 * 1024
MAX_SPECTATORS = 16
CLIENT_VERSION = '4.1.0'
NETWORK_PROTOCOL = 3
_MAX_PENDING = 4 * (MAX_FRAME_SIZE + 4)
_MAX_CONNECTIONS = 64
_HANDSHAKE_TIMEOUT = 10.0
_FRAME_TIMEOUT = 30.0
_KEEPALIVE_IDLE = 30
_KEEPALIVE_INTERVAL = 10
_KEEPALIVE_COUNT = 3
_LOGGER = logging.getLogger(__name__)


class ProtocolError(ValueError):
    """A malformed, oversized, or non-JSON-object network message."""


def _reject_constant(value):
    raise ProtocolError('Non-finite JSON numbers are not allowed.')


def _object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolError('Duplicate JSON fields are not allowed.')
        result[key] = value
    return result


def _encode(message):
    if not isinstance(message, dict):
        raise ProtocolError('Messages must be JSON objects.')
    try:
        payload = json.dumps(message, ensure_ascii=False, allow_nan=False,
                             separators=(',', ':')).encode('utf-8')
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ProtocolError('Message is not valid JSON.') from exc
    if not 0 < len(payload) <= MAX_FRAME_SIZE:
        raise ProtocolError('Message exceeds the 256 KiB limit.')
    return struct.pack('!I', len(payload)) + payload


class _Decoder:
    def __init__(self):
        self.buffer = bytearray()

    def feed(self, data):
        self.buffer.extend(data)
        while len(self.buffer) >= 4:
            size = struct.unpack_from('!I', self.buffer)[0]
            if not 0 < size <= MAX_FRAME_SIZE:
                raise ProtocolError('Invalid frame size (maximum 256 KiB).')
            if len(self.buffer) < size + 4:
                return
            payload = bytes(self.buffer[4:size + 4])
            del self.buffer[:size + 4]
            try:
                message = json.loads(payload.decode('utf-8'),
                                     parse_constant=_reject_constant,
                                     object_pairs_hook=_object_pairs)
            except (ValueError, UnicodeError, RecursionError) as exc:
                raise ProtocolError('Invalid JSON message.') from exc
            if not isinstance(message, dict):
                raise ProtocolError('Messages must be JSON objects.')
            yield message


def _string(value, field, maximum=128, empty=True):
    if not isinstance(value, str) or len(value) > maximum or (not empty and not value):
        raise ValueError('Invalid {}.'.format(field))
    # Reject unpaired surrogates, which cannot be transmitted as UTF-8.
    try:
        value.encode('utf-8')
    except UnicodeError as exc:
        raise ValueError('Invalid {}.'.format(field)) from exc
    return value


def _safe_text(value, maximum, fallback=''):
    """Neutralize Ren'Py text tags/interpolation, control and bidi characters."""
    value = _string(value, 'text', 4096)
    value = value.translate(str.maketrans('', '', '{}[]'))
    value = ''.join(c for c in value if not unicodedata.category(c).startswith('C'))
    return ' '.join(value.split())[:maximum] or fallback


def _secret_matches(actual, supplied):
    return hmac.compare_digest(actual.encode('utf-8'), supplied.encode('utf-8'))


def _close_socket(sock):
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    sock.close()


def _configure_keepalive(sock):
    """Detect unreachable clients without requiring a new client protocol.

    TCP probes work even while a player is thinking or the UI is idle. Once
    the OS reports a dead connection, the normal drop/reconnect rules apply.
    """
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    except OSError:
        _LOGGER.warning('Unable to enable TCP keepalive', exc_info=True)
        return
    if hasattr(socket, 'SIO_KEEPALIVE_VALS'):
        try:
            sock.ioctl(socket.SIO_KEEPALIVE_VALS,
                       (1, _KEEPALIVE_IDLE * 1000, _KEEPALIVE_INTERVAL * 1000))
        except OSError:
            _LOGGER.warning('Unable to configure TCP keepalive timing', exc_info=True)
    else:
        # Linux uses TCP_KEEPIDLE; macOS exposes the idle time as TCP_KEEPALIVE.
        idle_option = getattr(socket, 'TCP_KEEPIDLE',
                              getattr(socket, 'TCP_KEEPALIVE', None))
        if idle_option is not None:
            try:
                sock.setsockopt(socket.IPPROTO_TCP, idle_option, _KEEPALIVE_IDLE)
            except OSError:
                _LOGGER.warning('Unable to configure TCP keepalive idle time', exc_info=True)
    for name, value in (('TCP_KEEPINTVL', _KEEPALIVE_INTERVAL),
                        ('TCP_KEEPCNT', _KEEPALIVE_COUNT)):
        option = getattr(socket, name, None)
        if option is not None:
            try:
                sock.setsockopt(socket.IPPROTO_TCP, option, value)
            except OSError:
                _LOGGER.warning('Unable to configure %s', name, exc_info=True)


class _Peer:
    def __init__(self, sock):
        self.sock = sock
        self.decoder = _Decoder()
        self.outgoing = bytearray()
        self.joined = False
        self.player_id = None
        self.role = None
        self.name = ''
        self.accepted_at = time.monotonic()
        self.partial_since = None
        self.closing_at = None


class RoomServer:
    """One selector thread owns all room and engine state; no UI calls needed."""

    def __init__(self, host='0.0.0.0', port=5555, room_name='Guild Room',
                 password='', allow_spectators=True, max_players=4):
        if type(max_players) is not int or not 1 <= max_players <= 5:
            raise ValueError('max_players must be between 1 and 5.')
        if type(port) is not int or not 0 <= port <= 65535:
            raise ValueError('Invalid port.')
        if type(allow_spectators) is not bool:
            raise ValueError('allow_spectators must be a boolean.')
        self.host = host
        self._port = port
        self.room_name = _safe_text(room_name, 64, 'Guild Room')
        self.password = _string(password, 'password', 256)
        self.allow_spectators = allow_spectators
        self.max_players = max_players
        self.host_token = secrets.token_urlsafe(32)
        self._host_id = None
        self._players = {}
        self._player_peers = {}
        self._resume_tokens = {}
        self._next_id = 0
        self._peers = {}
        self._chat = collections.deque(maxlen=50)
        self._engine = None
        self._selector = None
        self._listener = None
        self._thread = None
        self._stop = threading.Event()
        self._lifecycle_lock = threading.Lock()
        self._dirty = False

    @property
    def port(self):
        """The actual bound port after start(), including when port=0 was used."""
        return self._port

    def start(self):
        with self._lifecycle_lock:
            if self._stop.is_set():
                raise RuntimeError('A closed server cannot be restarted.')
            if self._thread is not None:
                return self
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            selector = selectors.DefaultSelector()
            try:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listener.bind((self.host, self._port))
                listener.listen(_MAX_CONNECTIONS)
                listener.setblocking(False)
                selector.register(listener, selectors.EVENT_READ, None)
            except BaseException:
                listener.close()
                selector.close()
                raise
            self._listener = listener
            self._selector = selector
            self._port = listener.getsockname()[1]
            self._thread = threading.Thread(target=self._run, name='GuildRoomServer', daemon=True)
            self._thread.start()
        return self

    def close(self):
        """Stop networking, close all sockets and wait for server cleanup."""
        with self._lifecycle_lock:
            self._stop.set()
            thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join()

    def _run(self):
        try:
            while not self._stop.is_set():
                for key, mask in self._selector.select(0.05):
                    if self._stop.is_set():
                        break
                    if key.data is None:
                        self._accept()
                    else:
                        self._service(key.data, mask)
                now = time.monotonic()
                self._maintenance()
                for peer in list(self._peers.values()):
                    if peer.closing_at is not None:
                        if now >= peer.closing_at:
                            self._drop(peer)
                    elif not peer.joined and now - peer.accepted_at >= _HANDSHAKE_TIMEOUT:
                        self._error(peer, 'Join timed out.', fatal=True)
                    elif peer.partial_since is not None and now - peer.partial_since >= _FRAME_TIMEOUT:
                        self._error(peer, 'Incomplete frame timed out.', fatal=True)
                if self._dirty:
                    self._dirty = False
                    self._broadcast_snapshots()
        finally:
            self._stop.set()
            for peer in list(self._peers.values()):
                self._drop(peer)
            self._selector.close()
            self._listener.close()

    def _maintenance(self):
        if self._engine and hasattr(self._engine,'rules'):
            from guild_clock import advance
            self._dirty = advance(self._engine) or self._dirty

    def _accept(self):
        for _ in range(16):
            try:
                sock, address = self._listener.accept()
            except BlockingIOError:
                return
            sock.setblocking(False)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            if len(self._peers) >= _MAX_CONNECTIONS:
                sock.close()
                continue
            _configure_keepalive(sock)
            peer = _Peer(sock)
            self._peers[sock] = peer
            self._selector.register(sock, selectors.EVENT_READ, peer)

    def _service(self, peer, mask):
        if peer.sock not in self._peers:
            return
        try:
            if mask & selectors.EVENT_READ and peer.closing_at is None:
                try:
                    data = peer.sock.recv(65536)
                except BlockingIOError:
                    data = None
                if data == b'':
                    self._drop(peer)
                    return
                if data:
                    for message in peer.decoder.feed(data):
                        self._command(peer, message)
                        if self._stop.is_set() or peer.closing_at is not None or peer.sock not in self._peers:
                            break
                    if peer.decoder.buffer:
                        if peer.partial_since is None:
                            peer.partial_since = time.monotonic()
                    else:
                        peer.partial_since = None
            if mask & selectors.EVENT_WRITE and peer.outgoing:
                try:
                    sent = peer.sock.send(peer.outgoing)
                except BlockingIOError:
                    sent = 0
                del peer.outgoing[:sent]
            if peer.sock in self._peers:
                if peer.closing_at is not None and not peer.outgoing:
                    self._drop(peer)
                else:
                    self._interest(peer)
        except ProtocolError as exc:
            self._error(peer, str(exc), fatal=True)
        except OSError:
            self._drop(peer)

    def _interest(self, peer):
        events = selectors.EVENT_READ if peer.closing_at is None else 0
        if peer.outgoing:
            events |= selectors.EVENT_WRITE
        if events:
            self._selector.modify(peer.sock, events, peer)
        else:
            self._drop(peer)

    def _send(self, peer, message):
        if peer.sock not in self._peers:
            return
        packet = _encode(message)
        if len(peer.outgoing) + len(packet) > _MAX_PENDING:
            self._drop(peer)
            return
        peer.outgoing.extend(packet)
        self._interest(peer)

    def _error(self, peer, message, fatal=False):
        if peer.sock not in self._peers:
            return
        if fatal:
            peer.closing_at = time.monotonic() + 2.0
        self._send(peer, {'type': 'error', 'message': _safe_text(str(message)[:4096], 500)})

    def _drop(self, peer):
        if self._peers.pop(peer.sock, None) is None:
            return
        try:
            self._selector.unregister(peer.sock)
        except (KeyError, ValueError):
            pass
        _close_socket(peer.sock)
        if not peer.joined:
            return
        pid = peer.player_id
        if peer.role == 'player' and self._player_peers.get(pid) is peer:
            del self._player_peers[pid]
            self._players[pid]['connected'] = False
            if self._engine is None:
                self._players[pid]['ready'] = False
        self._dirty = True

    def _join(self, peer, message):
        if message.get('type') != 'join':
            raise ValueError('Join the room first.')
        role = message.get('role', 'player')
        if role not in ('player', 'spectator'):
            raise ValueError('Invalid role.')
        password = _string(message.get('password', ''), 'password', 256)
        if not _secret_matches(self.password, password):
            raise ValueError('Incorrect room password.')
        host_token = _string(message.get('host_token', ''), 'host token')
        resume_token = _string(message.get('resume_token', ''), 'resume token')
        claims_host = bool(host_token)
        if claims_host and (role != 'player' or not _secret_matches(self.host_token, host_token)):
            raise ValueError('Invalid host token.')
        name = _safe_text(message.get('name', ''), 32,
                          'Spectator' if role == 'spectator' else 'Player')
        pid = None
        if role == 'spectator':
            if resume_token:
                raise ValueError('Spectators do not have player resume tokens.')
            if not self.allow_spectators:
                raise ValueError('Spectators are not allowed in this room.')
            if sum(p.joined and p.role == 'spectator' for p in self._peers.values()) >= MAX_SPECTATORS:
                raise ValueError('The spectator seats are full.')
        elif resume_token:
            pid = self._resume_tokens.get(resume_token)
            if pid is None or pid not in self._players:
                raise ValueError('Invalid or expired resume token.')
            if pid in self._player_peers:
                raise ValueError('This player is already connected.')
            if claims_host and self._host_id not in (None, pid):
                raise ValueError('The host is already assigned.')
            name = self._players[pid]['name']
            self._players[pid]['connected'] = True
        else:
            if self._engine is not None:
                raise ValueError('The game has started. Join as a spectator or resume a player.')
            if len(self._players) >= self.max_players:
                raise ValueError('The room is full.')
            if claims_host and self._host_id is not None:
                raise ValueError('The host is already assigned.')
            pid = self._next_id
            self._next_id += 1
            self._players[pid] = {'id': pid, 'name': name, 'hero': 'bai_white',
                                  'bot': False, 'ready': False, 'connected': True}
            resume_token = secrets.token_urlsafe(32)
            self._resume_tokens[resume_token] = pid
        peer.joined = True
        peer.player_id = pid
        peer.role = role
        peer.name = name
        if role == 'player':
            self._player_peers[pid] = peer
        if claims_host:
            self._host_id = pid
        self._send(peer, {'type': 'welcome', 'player_id': pid, 'role': role,
                          'resume_token': resume_token, 'is_host': pid is not None and pid == self._host_id})
        self._dirty = True

    def _command(self, peer, message):
        try:
            if not peer.joined:
                self._join(peer, message)
                return
            kind = message.get('type')
            if 'player_id' in message:
                raise ValueError('Player identity is assigned by the server.')
            if kind == 'chat':
                content = _safe_text(message.get('message', ''), 500)
                if not content:
                    raise ValueError('Chat message is empty.')
                chat = {'type': 'chat', 'player_id': peer.player_id, 'name': peer.name,
                        'role': peer.role, 'message': content}
                self._chat.append(chat)
                for recipient in list(self._peers.values()):
                    if recipient.joined and recipient.closing_at is None:
                        self._send(recipient, chat)
                self._dirty = True
                return
            if peer.role != 'player':
                raise ValueError('Spectators are read-only.')
            if kind in ('start', 'return_lobby', 'end_session') and peer.player_id != self._host_id:
                raise ValueError('Only the host can do that.')
            if kind == 'end_session':
                self._stop.set()
                return
            if kind == 'return_lobby':
                if self._engine is None or self._engine.state['phase'] != 'finished':
                    raise ValueError('Return to lobby is only available after the game finishes.')
                self._engine = None
                for player in self._players.values():
                    player['ready'] = False
                self._dirty = True
                return
            if kind == 'action':
                if self._engine is None:
                    raise ValueError('The game has not started.')
                self._maintenance()
                if self._pause_info()[0]:
                    raise ValueError('Game paused: waiting for a disconnected player to reconnect.')
                action = message.get('action')
                if not isinstance(action, dict):
                    raise ValueError('action must be a JSON object.')
                # Any action-internal targets belong to the engine's rules;
                # they can never replace the authenticated actor argument.
                self._engine.apply(peer.player_id, action)
                self._dirty = True
                return
            if self._engine is not None:
                raise ValueError('Lobby settings cannot change after the game starts.')
            if kind == 'set_hero':
                from guild_content import hero_selection, selectable_hero
                hero = (hero_selection(message.get('character'), message.get('variant'))
                        if 'character' in message or 'variant' in message
                        else selectable_hero(message.get('hero')))
                self._players[peer.player_id]['hero'] = hero
                self._players[peer.player_id]['ready'] = False
            elif kind == 'ready':
                ready = message.get('ready', True)
                if type(ready) is not bool:
                    raise ValueError('ready must be a boolean.')
                self._players[peer.player_id]['ready'] = ready
            elif kind == 'start':
                if not all(player['connected'] for player in self._players.values()):
                    raise ValueError('All players must be connected before starting.')
                if not all(player['ready'] for player in self._players.values()):
                    raise ValueError('All players must be ready before starting.')
                seed = message.get('seed')
                if seed is not None and type(seed) is not int:
                    raise ValueError('seed must be an integer or null.')
                specs = [{key: player[key] for key in ('id', 'name', 'hero', 'bot')}
                         for player in self._players.values()]
                self._engine = self._make_engine(specs, seed)
            else:
                raise ValueError('Unknown command.')
            self._dirty = True
        except ValueError as exc:
            self._error(peer, str(exc), fatal=not peer.joined)
        except Exception:
            _LOGGER.exception('Room command failed')
            self._error(peer, 'The server could not process this command.', fatal=not peer.joined)

    @staticmethod
    def _make_engine(player_specs, seed):
        # Lazy import keeps lobbies and tests independent of engine import order.
        from guild_engine import Engine
        return Engine(player_specs, seed=seed)

    def _pause_info(self):
        if self._engine is None:
            return False, []
        state = self._engine.state
        if state.get('pending'):
            pid = state['pending']['player']
            waiting = [] if self._players[pid]['connected'] or any(p['id']==pid and p.get('withdrawn') for p in state['players']) else [pid]
            return bool(waiting), waiting
        if state['phase'] in ('action', 'final'):
            pid = state['players'][state['turn']]['id']
            waiting = [] if self._players[pid]['connected'] or any(p['id']==pid and p.get('withdrawn') for p in state['players']) else [pid]
            return bool(waiting), waiting
        if state['phase'] in ('research','draft'):
            pending = [p['id'] for p in state['players'] if
                       (p.get('draft_choice') is None if state['phase']=='draft' else not p.get('researched', False))]
            waiting = [pid for pid in pending if not self._players[pid]['connected'] and not any(p['id']==pid and p.get('withdrawn') for p in state['players'])]
            return bool(waiting) and len(waiting) == len(pending), waiting
        return False, []

    def _room_view(self):
        paused, waiting = self._pause_info()
        return {'name': self.room_name, 'host_id': self._host_id,
                'players': [dict(player) for player in self._players.values()],
                'spectators': sum(p.joined and p.role == 'spectator' and p.closing_at is None
                                  for p in self._peers.values()),
                'started': self._engine is not None, 'allow_spectators': self.allow_spectators,
                'max_players': self.max_players, 'paused': paused,
                'waiting_for': waiting, 'chat': list(self._chat)}

    def _broadcast_snapshots(self):
        room = self._room_view()
        for peer in list(self._peers.values()):
            if not peer.joined or peer.closing_at is not None:
                continue
            try:
                game = None if self._engine is None else self._engine.view(peer.player_id)
                self._send(peer, {'type': 'snapshot', 'room': room, 'game': game})
            except Exception:
                # Never fall back to state/export: those contain private cards.
                _LOGGER.exception('Could not serialize private-filtered snapshot')
                self._error(peer, 'The server could not create a game snapshot.')


class Client:
    """Threaded client with bounded queues; poll() is safe from a UI timer."""

    def __init__(self, host, port, name, role='player', password='',
                 host_token='', resume_token='', lobby=False,
                 client_version=CLIENT_VERSION):
        if role not in ('player', 'spectator'):
            raise ValueError('Invalid role.')
        self.host = host
        self.port = port
        self.name = name
        self.role = role
        self.password = password
        self.host_token = host_token
        self.resume_token = resume_token
        self.lobby = lobby
        self.client_version = client_version
        self.player_id = None
        self.is_host = False
        self._sock = None
        self._thread = None
        self._stop = threading.Event()
        self._connected = threading.Event()
        self._lifecycle_lock = threading.Lock()
        self._outgoing = queue.Queue(maxsize=128)
        self._messages = collections.deque()
        self._messages_lock = threading.Lock()
        self._pending_bytes = 0
        self._pending_lock = threading.Lock()

    @property
    def connected(self):
        return self._connected.is_set()

    def connect(self):
        """Connect TCP and start asynchronous handshake; failures also reach poll()."""
        with self._lifecycle_lock:
            if self._thread is not None or self._stop.is_set():
                raise RuntimeError('Use a new Client instance to reconnect.')
            join = _encode({'type': 'hello' if self.lobby else 'join', 'name': self.name, 'role': self.role,
                            'password': self.password, 'host_token': self.host_token,
                            'resume_token': self.resume_token, 'client_version': self.client_version,
                            'protocol': NETWORK_PROTOCOL})
            sock = None
            try:
                sock = socket.create_connection((self.host, self.port), timeout=5.0)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except OSError as exc:
                if sock is not None:
                    sock.close()
                self._stop.set()
                self._deliver({'type': 'error', 'message': str(exc)})
                self._deliver({'type': 'disconnected', 'message': 'Connection failed.'})
                raise
            sock.setblocking(False)
            self._sock = sock
            self._connected.set()
            self._thread = threading.Thread(target=self._run, args=(join,),
                                            name='GuildRoomClient', daemon=True)
            self._thread.start()
        return self

    def send(self, action):
        """Queue a complete command dict; raises ValueError/OSError on local failure."""
        packet = _encode(action)
        with self._pending_lock:
            if not self.connected or self._stop.is_set():
                raise OSError('Client is not connected.')
            if self._pending_bytes + len(packet) > _MAX_PENDING:
                raise OSError('Client send queue is full.')
            try:
                self._outgoing.put_nowait(packet)
            except queue.Full as exc:
                raise OSError('Client send queue is full.') from exc
            self._pending_bytes += len(packet)

    def poll(self):
        """Return all currently queued messages, immediately (possibly [])."""
        with self._messages_lock:
            messages = list(self._messages)
            self._messages.clear()
        return messages

    def close(self):
        with self._lifecycle_lock:
            self._stop.set()
            self._connected.clear()
            if self._sock is not None:
                _close_socket(self._sock)
            thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join()

    def _deliver(self, message):
        with self._messages_lock:
            # A paused UI needs only the newest snapshot. Keep control messages
            # and recent chat, but cap their memory too if it never polls again.
            if message.get('type') == 'snapshot':
                self._messages = collections.deque(
                    item for item in self._messages if item.get('type') != 'snapshot')
            if len(self._messages) >= 256:
                # Preserve the initial welcome/token even during chat floods.
                index = next((i for i, item in enumerate(self._messages)
                              if item.get('type') != 'welcome'), 0)
                del self._messages[index]
            self._messages.append(message)

    def _run(self, join):
        decoder = _Decoder()
        outgoing = bytearray(join)
        queued_bytes = 0
        selector = selectors.DefaultSelector()
        reason = 'Connection closed.'
        try:
            selector.register(self._sock, selectors.EVENT_READ | selectors.EVENT_WRITE)
            while not self._stop.is_set():
                if not outgoing:
                    try:
                        packet = self._outgoing.get_nowait()
                    except queue.Empty:
                        pass
                    else:
                        outgoing.extend(packet)
                        queued_bytes = len(packet)
                events = selectors.EVENT_READ | (selectors.EVENT_WRITE if outgoing else 0)
                selector.modify(self._sock, events)
                for _key, mask in selector.select(0.05):
                    if mask & selectors.EVENT_READ:
                        try:
                            data = self._sock.recv(65536)
                        except BlockingIOError:
                            data = None
                        if data == b'':
                            return
                        if data:
                            for message in decoder.feed(data):
                                if message.get('type') == 'welcome':
                                    self.player_id = message['player_id']
                                    self.resume_token = message.get('resume_token', '')
                                    self.is_host = message.get('is_host', False)
                                self._deliver(message)
                    if mask & selectors.EVENT_WRITE and outgoing:
                        try:
                            sent = self._sock.send(outgoing)
                        except BlockingIOError:
                            sent = 0
                        del outgoing[:sent]
                        if not outgoing and queued_bytes:
                            with self._pending_lock:
                                self._pending_bytes -= queued_bytes
                            queued_bytes = 0
        except OSError as exc:
            if not self._stop.is_set():
                reason = str(exc)
                self._deliver({'type': 'error', 'message': str(exc)})
        except (ValueError, KeyError) as exc:
            if not self._stop.is_set():
                reason = 'Connection lost.'
                self._deliver({'type': 'error', 'message': str(exc)})
        finally:
            self._stop.set()
            self._connected.clear()
            selector.close()
            _close_socket(self._sock)
            self._deliver({'type': 'disconnected', 'message': reason})


# Compatibility spelling for callers that group RoomServer and RoomClient.
RoomClient = Client
