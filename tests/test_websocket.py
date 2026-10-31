"""Real lobby exchanges through HTTP upgrade, including protocol rejection."""
import json
from pathlib import Path
import socket
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'guild-server'), str(ROOT / 'tools')]
from guild_lobby import LobbyServer
from guild_site import SiteWeb
from check_public_connection import SocketProbe, masked_frame


class WebSocketIntegration(unittest.TestCase):
    def setUp(self):
        self.game = LobbyServer('127.0.0.1', 0).start()
        self.site = SiteWeb(ROOT / 'guild-server/site', host='127.0.0.1', port=0,
                            game_endpoint=('127.0.0.1', self.game.port)).start()
        self.addCleanup(self.game.close)
        self.addCleanup(self.site.close)

    def client(self):
        client = SocketProbe('127.0.0.1', self.site.port)
        self.addCleanup(client.close)
        return client

    def test_real_welcome_directory_create_and_leave(self):
        client = self.client()
        client.send(dict(type='hello', name='RelayTest', client_version='4.1.0', protocol=3))
        self.assertEqual(client.wait('server_welcome')['type'], 'server_welcome')
        self.assertEqual(client.wait('directory')['rooms'], [])
        client.send(dict(type='create_room', room_name='RelayTest', max_players=1))
        self.assertEqual(client.wait('welcome')['role'], 'player')
        self.assertEqual(client.wait('snapshot')['room']['name'], 'RelayTest')
        client.send(dict(type='leave_room'))
        self.assertEqual(client.wait('left_room')['type'], 'left_room')

    def test_fragmented_application_hello_and_ping(self):
        client = self.client()
        data = json.dumps(dict(type='hello', name='Fragments', client_version='4.1.0', protocol=3)).encode()
        data = struct.pack('!I', len(data)) + data
        packets = masked_frame(data[:7], final=False) + masked_frame(b'ping-check', 9) + masked_frame(data[7:], 0)
        # TCP boundaries can split both WebSocket headers and payloads.
        for part in [packets[:1], packets[1:4], packets[4:11], packets[11:]]:
            client.sock.sendall(part)
        opcode, payload = client.packet()
        self.assertEqual((opcode, payload), (10, b'ping-check'))
        client.wait('server_welcome')
        client.wait('directory')

    def test_unmasked_and_oversized_frames_are_closed(self):
        for bad in [b'\x82\x02{}', b'\x82\xff' + struct.pack('!Q', 262149)]:
            with self.subTest(frame=bad):
                client = self.client()
                client.sock.sendall(bad)
                self.assertEqual(client.packet(), (8, struct.pack('!H', 1002)))

    def test_cross_origin_upgrade_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, '403'):
            SocketProbe('127.0.0.1', self.site.port, origin='https://unrelated.example')

    def test_existing_http_status_still_works(self):
        import urllib.request
        with urllib.request.urlopen('http://127.0.0.1:%s/api/health' % self.site.port, timeout=3) as response:
            self.assertTrue(json.load(response)['online'])


if __name__ == '__main__':
    unittest.main()
