"""Require an application welcome and directory over the public WebSocket route."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def masked_frame(data, opcode=2, final=True):
    mask = os.urandom(4)
    prefix = bytes(((128 if final else 0) | opcode,))
    length = len(data)
    prefix += bytes((128 | length,)) if length < 126 else b'\xfe' + struct.pack('!H', length) if length <= 65535 else b'\xff' + struct.pack('!Q', length)
    return prefix + mask + bytes(value ^ mask[i % 4] for i, value in enumerate(data))


class SocketProbe:
    def __init__(self, host, port, origin=None):
        self.sock = socket.create_connection((host, port), timeout=8)
        self.sock.settimeout(12)
        self.buffer = bytearray()
        self.messages = []
        key = base64.b64encode(os.urandom(16)).decode()
        request = ('GET /game/socket HTTP/1.1\r\nHost: %s:%s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Version: 13\r\nSec-WebSocket-Key: %s\r\n' % (host, port, key))
        if origin:
            request += 'Origin: ' + origin + '\r\n'
        self.sock.sendall((request + '\r\n').encode('ascii'))
        header = bytearray()
        while b'\r\n\r\n' not in header:
            value = self.sock.recv(1)
            if not value or len(header) > 8192:
                raise RuntimeError('Missing HTTP upgrade')
            header.extend(value)
        expected = base64.b64encode(hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest())
        if not header.startswith(b'HTTP/1.1 101 ') or expected not in header:
            self.close()
            raise RuntimeError('Upgrade rejected: ' + header.split(b'\r\n')[0].decode())

    def close(self):
        self.sock.close()

    def exact(self, count):
        data = bytearray()
        while len(data) < count:
            part = self.sock.recv(count - len(data))
            if not part:
                raise EOFError('Connection ended before application response')
            data.extend(part)
        return bytes(data)

    def packet(self):
        first, second = self.exact(2)
        if second & 128:
            raise RuntimeError('Server frames must be unmasked')
        count = second & 127
        if count in (126, 127):
            count = int.from_bytes(self.exact(2 if count == 126 else 8), 'big')
        if count > 1048592:
            raise RuntimeError('Oversized server packet')
        return first & 15, self.exact(count)

    def send(self, message):
        data = json.dumps(message, ensure_ascii=False).encode('utf8')
        self.sock.sendall(masked_frame(struct.pack('!I', len(data)) + data))

    def wait(self, kind, timeout=12):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for index, message in enumerate(self.messages):
                if message.get('type') == kind:
                    return self.messages.pop(index)
                if message.get('type') == 'error':
                    raise RuntimeError(message['message'])
            opcode, data = self.packet()
            if opcode == 8:
                raise EOFError('Server closed WebSocket')
            if opcode == 9:
                self.sock.sendall(masked_frame(data, 10))
            if opcode != 2:
                continue
            self.buffer.extend(data)
            while len(self.buffer) >= 4:
                count = int.from_bytes(self.buffer[:4], 'big')
                if not 0 < count <= 262144:
                    raise RuntimeError('Invalid application frame')
                if len(self.buffer) < count + 4:
                    break
                self.messages.append(json.loads(self.buffer[4:count + 4]))
                del self.buffer[:count + 4]
        raise TimeoutError('No application ' + kind)


def verify(host='guanpeng666.cn', port=6680):
    client = SocketProbe(host, port)
    try:
        client.send(dict(type='hello', name='PublicConnectionCheck', client_version='4.1.0', protocol=3))
        welcome = client.wait('server_welcome')
        directory = client.wait('directory')
        return dict(host=host, port=port, transport='websocket', welcome=welcome['type'], directory_received=True, rooms=len(directory['rooms']))
    finally:
        client.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='guanpeng666.cn')
    parser.add_argument('--port', type=int, default=6680)
    args = parser.parse_args()
    print(json.dumps(verify(args.host, args.port), ensure_ascii=False, indent=2))
