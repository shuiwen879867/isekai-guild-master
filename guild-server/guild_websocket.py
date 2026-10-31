"""Bounded RFC6455 binary relay to this process's fixed game listener."""
import base64
import hashlib
import select
import socket
import struct
import time
from urllib.parse import urlsplit

MAX_MESSAGE = 262144 + 4
MAX_PENDING = 4 * MAX_MESSAGE
GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'


class WebSocketError(ValueError):
    pass


def frame(payload=b'', opcode=2):
    length = len(payload)
    prefix = bytes((0x80 | opcode,))
    if length < 126:
        return prefix + bytes((length,)) + payload
    if length <= 65535:
        return prefix + b'\x7e' + struct.pack('!H', length) + payload
    return prefix + b'\x7f' + struct.pack('!Q', length) + payload


class ClientFrames:
    """Incremental masked-frame parser, including fragmented binary messages."""

    def __init__(self):
        self.buffer = bytearray()
        self.fragment = None
        self.fragments = 0

    def feed(self, data):
        self.buffer.extend(data)
        events = []
        while len(self.buffer) >= 2:
            first, second = self.buffer[:2]
            final, opcode = bool(first & 128), first & 15
            if first & 112 or not second & 128 or opcode not in (0, 2, 8, 9, 10):
                raise WebSocketError('Invalid opcode, extension or client masking')
            length, offset = second & 127, 2
            if length in (126, 127):
                size = 2 if length == 126 else 8
                if len(self.buffer) < offset + size:
                    break
                length = int.from_bytes(self.buffer[offset:offset + size], 'big')
                if length < (126 if size == 2 else 65536):
                    raise WebSocketError('Non-minimal frame length')
                offset += size
            if length > MAX_MESSAGE or (opcode >= 8 and (not final or length > 125)):
                raise WebSocketError('Oversized or fragmented control frame')
            if len(self.buffer) < offset + 4 + length:
                break
            mask = self.buffer[offset:offset + 4]
            offset += 4
            payload = bytes(value ^ mask[i % 4] for i, value in enumerate(self.buffer[offset:offset + length]))
            del self.buffer[:offset + length]
            if opcode >= 8:
                if opcode == 8:
                    if len(payload) == 1:
                        raise WebSocketError('Invalid close payload')
                    if len(payload) >= 2:
                        code = int.from_bytes(payload[:2], 'big')
                        if code < 1000 or code in (1004, 1005, 1006, 1015) or 1016 <= code < 3000 or code >= 5000:
                            raise WebSocketError('Invalid close code')
                        try:
                            payload[2:].decode('utf8')
                        except UnicodeDecodeError as exc:
                            raise WebSocketError('Invalid close reason') from exc
                events.append((opcode, payload))
                continue
            if opcode == 2:
                if self.fragment is not None:
                    raise WebSocketError('Overlapping fragmented messages')
                if final:
                    events.append((2, payload))
                    continue
                self.fragment, self.fragments = bytearray(), 0
            elif self.fragment is None:
                raise WebSocketError('Unexpected continuation')
            self.fragments += 1
            if len(self.fragment) + len(payload) > MAX_MESSAGE or self.fragments > 1024:
                raise WebSocketError('Oversized fragmented message')
            self.fragment.extend(payload)
            if final:
                events.append((2, bytes(self.fragment)))
                self.fragment = None
        if len(self.buffer) > MAX_MESSAGE + 14:
            raise WebSocketError('Receive buffer exceeded')
        return events


def upgrade(handler, endpoint, stop, slots):
    """Validate an upgrade, then relay only to the configured local endpoint."""
    headers = handler.headers
    origin = headers.get('Origin')
    if origin:
        parsed = urlsplit(origin)
        if parsed.scheme not in ('http', 'https') or parsed.netloc.lower() != headers.get('Host', '').lower():
            handler.send_error(403)
            return
    try:
        key = headers.get('Sec-WebSocket-Key', '')
        valid_key = len(base64.b64decode(key, validate=True)) == 16
    except ValueError:
        valid_key = False
    if (handler.head_only or handler.request_version != 'HTTP/1.1' or
            headers.get('Upgrade', '').lower() != 'websocket' or
            'upgrade' not in [token.strip().lower() for token in headers.get('Connection', '').split(',')] or
            headers.get('Sec-WebSocket-Version') != '13' or not valid_key):
        handler.send_error(400, 'WebSocket upgrade required')
        return
    if not slots.acquire(blocking=False):
        handler.send_error(503)
        return
    try:
        try:
            backend = socket.create_connection(endpoint, timeout=3)
        except OSError:
            handler.send_error(503)
            return
        with backend:
            accept = base64.b64encode(hashlib.sha1((key + GUID).encode('ascii')).digest()).decode('ascii')
            handler.protocol_version = 'HTTP/1.1'
            handler.send_response(101, 'Switching Protocols')
            handler.send_header('Upgrade', 'websocket')
            handler.send_header('Connection', 'Upgrade')
            handler.send_header('Sec-WebSocket-Accept', accept)
            handler.end_headers()
            handler.wfile.flush()
            handler.close_connection = True
            relay(handler.connection, backend, stop)
    finally:
        slots.release()


def relay(client, backend, stop):
    client.setblocking(False)
    backend.setblocking(False)
    parser = ClientFrames()
    to_client, to_game = bytearray(), bytearray()
    last_input = last_ping = time.monotonic()
    closing = False
    close_deadline = 0
    try:
        while not stop.is_set():
            now = time.monotonic()
            if closing:
                if not to_client or now >= close_deadline:
                    return
            elif now - last_input > 90:
                return
            elif now - last_ping >= 20:
                to_client.extend(frame(b'guild', 9))
                last_ping = now
            readers = [] if closing else [client, backend]
            writers = ([client] if to_client else []) + ([backend] if to_game and not closing else [])
            readable, writable, _ = select.select(readers, writers, [], 1)
            for connection in readable:
                try:
                    data = connection.recv(65536)
                except BlockingIOError:
                    continue
                if not data:
                    if connection is client:
                        return
                    to_client.extend(frame(struct.pack('!H', 1000), 8))
                    closing, close_deadline = True, time.monotonic() + 2
                    break
                if connection is backend:
                    to_client.extend(frame(data))
                else:
                    last_input = time.monotonic()
                    try:
                        for opcode, payload in parser.feed(data):
                            if opcode == 2:
                                to_game.extend(payload)
                            elif opcode == 9:
                                to_client.extend(frame(payload, 10))
                            elif opcode == 8:
                                to_client.extend(frame(payload, 8))
                                closing, close_deadline = True, time.monotonic() + 2
                                break
                    except WebSocketError:
                        to_client.extend(frame(struct.pack('!H', 1002), 8))
                        closing, close_deadline = True, time.monotonic() + 2
            if len(to_client) > MAX_PENDING or len(to_game) > MAX_PENDING:
                return
            for connection in writable:
                pending = to_client if connection is client else to_game
                try:
                    sent = connection.send(pending)
                except BlockingIOError:
                    continue
                del pending[:sent]
    except (OSError, ValueError):
        pass
