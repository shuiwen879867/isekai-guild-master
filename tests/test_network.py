"""Stdlib socket integration tests: python -B -m unittest discover -s tests -p test_network.py -v.

The contract stub lives only here; production always imports guild_engine.Engine.
The real-engine test runs automatically once guild_engine.py is available.
"""

import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"guild-server"))

import collections
import copy
import importlib.util
import json
import socket
import struct
import time
import unittest
from types import SimpleNamespace
from unittest import mock

import guild_network as network


class ContractEngine:
    """Small deterministic human-only engine to isolate networking behavior."""

    def __init__(self, player_specs, seed=None):
        self.state = {'phase': 'research', 'turn': 0, 'players': copy.deepcopy(player_specs),
                      'revision': 0, 'last_actor': None, 'seed': seed}
        for player in self.state['players']:
            player.update(researched=False, hand=[],
                          offered=['private-{}-{}'.format(player['id'], i) for i in range(3)])

    def apply(self, player_id, action):
        player = next(p for p in self.state['players'] if p['id'] == player_id)
        kind = action.get('type')
        if kind == 'research' and self.state['phase'] == 'research' and not player['researched']:
            cards = action.get('cards', [])
            if not isinstance(cards, list) or any(card not in player['offered'] for card in cards):
                raise ValueError('Invalid research cards.')
            player['hand'] = list(cards)
            player['offered'] = []
            player['researched'] = True
            if all(p['researched'] for p in self.state['players']):
                self.state['phase'] = 'action'
        elif kind == 'pass' and self.state['phase'] in ('action', 'final'):
            if self.state['players'][self.state['turn']]['id'] != player_id:
                raise ValueError('Not your turn.')
            self.state['turn'] += 1
            if self.state['turn'] == len(self.state['players']):
                self.state['turn'] = 0
                self.state['phase'] = 'final' if self.state['phase'] == 'action' else 'finished'
        else:
            raise ValueError('Invalid action.')
        self.state['revision'] += 1
        self.state['last_actor'] = player_id

    def view(self, player_id=None):
        result = copy.deepcopy(self.state)
        for player in result['players']:
            player['hand_count'] = len(player['hand'])
            player['offered_count'] = len(player['offered'])
            if player['id'] != player_id:
                del player['hand']
                del player['offered']
        return result

    def bot_action(self, player_id):
        raise AssertionError('The networking module must never call bot_action.')

    def export(self):
        raise AssertionError('Private export data must never be used for snapshots.')


class SocketCase(unittest.TestCase):
    def setUp(self):
        self.pending = collections.defaultdict(collections.deque)

    def room(self, **kwargs):
        server = network.RoomServer(host='127.0.0.1', port=0, **kwargs).start()
        self.addCleanup(server.close)
        return server

    def client(self, server, name='Player', **kwargs):
        client = network.Client('127.0.0.1', server.port, name, **kwargs)
        self.addCleanup(client.close)
        client.connect()
        return client

    def joined(self, server, name='Player', **kwargs):
        client = self.client(server, name, **kwargs)
        self.wait(client, lambda message: message.get('type') == 'welcome')
        return client

    def wait(self, client, predicate, timeout=4.0):
        deadline = time.monotonic() + timeout
        seen = []
        while time.monotonic() < deadline:
            self.pending[client].extend(client.poll())
            while self.pending[client]:
                message = self.pending[client].popleft()
                if predicate(message):
                    return message
                seen.append(message)
            time.sleep(0.01)
        self.fail('Timed out waiting for message; last messages: {!r}'.format(seen[-4:]))

    def snapshot(self, client, predicate=lambda message: True):
        return self.wait(client, lambda message: message.get('type') == 'snapshot' and predicate(message))

    def error(self, client, contains):
        message = self.wait(client, lambda item: item.get('type') == 'error')
        self.assertIn(contains.lower(), message['message'].lower())
        return message

    def ready(self, client):
        client.send({'type': 'ready', 'ready': True})
        return self.snapshot(client, lambda message: any(
            p['id'] == client.player_id and p['ready'] for p in message['room']['players']))

    def start(self, server, clients):
        for client in clients:
            self.ready(client)
        host = next(client for client in clients if client.is_host)
        host.send({'type': 'start', 'seed': 7})
        return self.snapshot(host, lambda message: message['room']['started'])

    def assert_private(self, game, owner_id):
        for player in game['players']:
            if player['id'] == owner_id:
                self.assertIn('hand', player)
                self.assertIn('offered', player)
            else:
                self.assertNotIn('hand', player)
                self.assertNotIn('offered', player)
                self.assertIn('hand_count', player)
                self.assertIn('offered_count', player)

    def two_players(self):
        server = self.room()
        host = self.joined(server, 'Host', host_token=server.host_token)
        guest = self.joined(server, 'Guest')
        self.start(server, [host, guest])
        return server, host, guest

    def research(self, client, cards=None):
        client.send({'type': 'action', 'action': {'type': 'research', 'cards': cards or []}})
        return self.snapshot(client, lambda message: message['game'] is not None and any(
            p['id'] == client.player_id and p['researched'] for p in message['game']['players']))


class KeepaliveTests(unittest.TestCase):
    def test_windows_and_unix_probe_configuration(self):
        for windows in (False, True):
            with self.subTest(windows=windows):
                api = SimpleNamespace(SOL_SOCKET=1, SO_KEEPALIVE=2, IPPROTO_TCP=3,
                                      TCP_KEEPIDLE=4, TCP_KEEPINTVL=5, TCP_KEEPCNT=6)
                if windows:
                    api.SIO_KEEPALIVE_VALS = 7
                sock = mock.Mock()
                with mock.patch.object(network, 'socket', api):
                    network._configure_keepalive(sock)
                sock.setsockopt.assert_any_call(1, 2, 1)
                sock.setsockopt.assert_any_call(3, 5, 10)
                sock.setsockopt.assert_any_call(3, 6, 3)
                if windows:
                    sock.ioctl.assert_called_once_with(7, (1, 30000, 10000))
                else:
                    sock.setsockopt.assert_any_call(3, 4, 30)
                    sock.ioctl.assert_not_called()

    def test_unsupported_probe_settings_do_not_reject_connection(self):
        api = SimpleNamespace(SOL_SOCKET=1, SO_KEEPALIVE=2, IPPROTO_TCP=3,
                              TCP_KEEPIDLE=4, TCP_KEEPINTVL=5, TCP_KEEPCNT=6)
        sock = mock.Mock()
        sock.setsockopt.side_effect = [None, OSError('unsupported'), None, None]
        with mock.patch.object(network, 'socket', api), self.assertLogs(network._LOGGER, 'WARNING'):
            network._configure_keepalive(sock)
        # Keepalive stays enabled; other supported options are still attempted.
        sock.setsockopt.assert_any_call(3, 6, 3)


class RoomTests(SocketCase):
    def setUp(self):
        super().setUp()
        patch = mock.patch.object(network.RoomServer, '_make_engine', side_effect=ContractEngine)
        patch.start()
        self.addCleanup(patch.stop)

    def test_accepted_connections_enable_keepalive(self):
        server = self.room()
        self.joined(server)
        peer = next(iter(server._peers.values()))
        self.assertEqual(peer.sock.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE), 1)

    def test_host_token_required_even_for_first_join_and_host_only_commands(self):
        server = self.room()
        guest = self.joined(server, 'First arrival')
        self.assertFalse(guest.is_host)
        for kind in ('start', 'return_lobby', 'end_session'):
            guest.send({'type': kind})
            self.error(guest, 'Only the host')
        impostor = self.client(server, host_token='not-the-token')
        self.error(impostor, 'host token')
        host = self.joined(server, 'Actual host', host_token=server.host_token)
        self.assertTrue(host.is_host)
        snapshot = self.snapshot(host)
        self.assertEqual(snapshot['room']['host_id'], host.player_id)
        self.assertEqual(len(snapshot['room']['players']), 2)
        for secret in (server.host_token, host.resume_token, guest.resume_token):
            self.assertNotIn(secret, json.dumps(snapshot))

    def test_ready_validation_hero_change_and_no_bot_commands(self):
        server = self.room()
        host = self.joined(server, host_token=server.host_token)
        host.send({'type': 'start'})
        self.error(host, 'ready')
        host.send({'type': 'ready', 'ready': 'yes'})
        self.error(host, 'boolean')
        self.ready(host)
        host.send({'type': 'set_hero', 'hero': 'hainie_red'})
        snapshot = self.snapshot(host, lambda m: m['room']['players'][0]['hero'] == 'hainie_red')
        self.assertFalse(snapshot['room']['players'][0]['ready'])
        for kind in ('add_bot', 'remove_bot'):
            host.send({'type': kind})
            self.error(host, 'Unknown command')
        self.assertFalse(snapshot['room']['players'][0]['bot'])

    def test_password_and_spectator_access(self):
        server = self.room(password='密碼', allow_spectators=False)
        wrong = self.client(server, password='wrong')
        self.error(wrong, 'password')
        denied = self.client(server, role='spectator', password='密碼')
        self.error(denied, 'not allowed')
        host = self.joined(server, password='密碼', host_token=server.host_token)
        snapshot = self.snapshot(host)
        self.assertEqual(snapshot['room']['spectators'], 0)
        self.assertEqual(len(snapshot['room']['players']), 1)

    def test_one_to_four_human_seats_and_full_rooms(self):
        for count in range(1, 5):
            with self.subTest(count=count):
                server = self.room(max_players=count)
                host = self.joined(server, 'Host', host_token=server.host_token)
                clients = [host] + [self.joined(server, 'Player {}'.format(i)) for i in range(1, count)]
                overflow = self.client(server)
                self.error(overflow, 'full')
                snapshot = self.start(server, clients)
                self.assertEqual(len(snapshot['game']['players']), count)
                self.assertTrue(all(not p['bot'] for p in snapshot['game']['players']))
                spectator = self.joined(server, role='spectator')
                self.assertEqual(self.snapshot(spectator)['room']['spectators'], 1)

    def test_two_clients_start_plus_late_spectator_and_private_views(self):
        server, host, guest = self.two_players()
        guest_view = self.snapshot(guest, lambda m: m['room']['started'])
        self.assert_private(guest_view['game'], guest.player_id)
        self.research(host, ['private-{}-0'.format(host.player_id)])
        spectator = self.joined(server, '{color=red}[Observer]\x00\u202e', role='spectator')
        self.assertIsNone(spectator.player_id)
        self.assertEqual(spectator.resume_token, '')
        observed = self.snapshot(spectator)
        self.assert_private(observed['game'], None)
        self.assertNotIn('private-', json.dumps(observed))
        spectator.send({'type': 'chat', 'message': '{b}[Hello]\x00\u202e'})
        chat = self.wait(host, lambda m: m.get('type') == 'chat')
        for text in (chat['name'], chat['message']):
            for unsafe in '{}[]\x00\u202e':
                self.assertNotIn(unsafe, text)
        for command in ({'type': 'set_hero', 'hero': 'bai_red'}, {'type': 'ready'},
                        {'type': 'start'}, {'type': 'end_session'}, {'type': 'return_lobby'},
                        {'type': 'action', 'action': {'type': 'research', 'cards': []}}):
            spectator.send(command)
            self.error(spectator, 'read-only')
        late_player = self.client(server)
        self.error(late_player, 'started')

    def test_identity_spoofing_and_invalid_actions_do_not_mutate(self):
        server, host, guest = self.two_players()
        guest.send({'type': 'action', 'player_id': host.player_id,
                    'action': {'type': 'research', 'cards': []}})
        self.error(guest, 'identity')
        guest.send({'type': 'action', 'action': []})
        self.error(guest, 'JSON object')
        guest.send({'type': 'action', 'action': {'type': 'not-real'}})
        self.error(guest, 'Invalid action')
        # Even a nested player_id never changes the actor passed to the engine.
        guest.send({'type': 'action', 'action': {'type': 'research', 'cards': [],
                                                'player_id': host.player_id}})
        snapshot = self.snapshot(guest, lambda m: m['game'] and m['game']['revision'] == 1)
        self.assertEqual(snapshot['game']['last_actor'], guest.player_id)
        self.assertFalse(snapshot['game']['players'][0]['researched'])

    def test_lobby_disconnect_holds_seat_resets_ready_and_resumes(self):
        server = self.room(max_players=2)
        host = self.joined(server, 'Host', host_token=server.host_token)
        guest = self.joined(server, 'Original guest')
        self.ready(host)
        self.ready(guest)
        token, pid = guest.resume_token, guest.player_id
        guest.close()
        disconnected = self.snapshot(host, lambda m: not m['room']['players'][1]['connected'])
        self.assertEqual(len(disconnected['room']['players']), 2)
        self.assertFalse(disconnected['room']['players'][1]['ready'])
        overflow = self.client(server)
        self.error(overflow, 'full')
        host.send({'type': 'start'})
        self.error(host, 'connected')
        resumed = self.joined(server, 'Changed name', resume_token=token)
        snapshot = self.snapshot(resumed)
        self.assertEqual(resumed.player_id, pid)
        self.assertEqual(snapshot['room']['players'][1]['name'], 'Original guest')
        self.assertTrue(snapshot['room']['players'][1]['connected'])
        self.ready(resumed)
        host.send({'type': 'start'})
        self.snapshot(host, lambda m: m['room']['started'])

    def test_current_actor_disconnect_pauses_without_ai_and_host_can_resume(self):
        server, host, guest = self.two_players()
        self.research(host)
        self.research(guest)
        self.snapshot(host, lambda m: m['game']['phase'] == 'action')
        token, pid = host.resume_token, host.player_id
        host.close()
        paused = self.snapshot(guest, lambda m: m['room']['paused'])
        self.assertEqual(paused['room']['waiting_for'], [pid])
        self.assertFalse(paused['room']['players'][0]['connected'])
        self.assertFalse(paused['room']['players'][0]['bot'])
        unchanged = copy.deepcopy(paused['game'])
        # Longer than the removed 0.5-second AI ticker; no UI polling needed.
        time.sleep(0.65)
        guest.send({'type': 'action', 'action': {'type': 'pass'}})
        self.error(guest, 'paused')
        guest.send({'type': 'chat', 'message': 'Still waiting'})
        self.assertEqual(self.snapshot(guest, lambda m: m['room']['chat'])['game'], unchanged)
        resumed = self.joined(server, resume_token=token)
        snapshot = self.snapshot(resumed)
        self.assertTrue(resumed.is_host)
        self.assertFalse(snapshot['room']['paused'])
        self.assertEqual(snapshot['game']['revision'], unchanged['revision'])
        resumed.send({'type': 'action', 'action': {'type': 'pass'}})
        progressed = self.snapshot(guest, lambda m: m['game']['turn'] == 1)
        self.assertEqual(progressed['game']['last_actor'], pid)
        duplicate = self.client(server, resume_token=token)
        self.error(duplicate, 'already connected')
        bad = self.client(server, resume_token='wrong')
        self.error(bad, 'resume token')

    def test_research_waits_for_disconnected_human_without_blocking_other_choices(self):
        server, host, guest = self.two_players()
        guest.close()
        snapshot = self.snapshot(host, lambda m: not m['room']['players'][1]['connected'])
        self.assertFalse(snapshot['room']['paused'])
        self.assertEqual(snapshot['room']['waiting_for'], [guest.player_id])
        snapshot = self.research(host)
        self.assertTrue(snapshot['room']['paused'])
        self.assertEqual(snapshot['game']['phase'], 'research')
        resumed = self.joined(server, resume_token=guest.resume_token)
        snapshot = self.snapshot(resumed)
        self.assertFalse(snapshot['room']['paused'])
        self.assert_private(snapshot['game'], guest.player_id)
        self.assertEqual(self.research(resumed)['game']['phase'], 'action')

    def test_disconnected_nonactor_does_not_pause_until_their_turn(self):
        server, host, guest = self.two_players()
        self.research(host)
        self.research(guest)
        guest.close()
        snapshot = self.snapshot(host, lambda m: not m['room']['players'][1]['connected'])
        self.assertFalse(snapshot['room']['paused'])
        host.send({'type': 'action', 'action': {'type': 'pass'}})
        self.assertEqual(self.snapshot(host, lambda m: m['room']['paused'])['room']['waiting_for'],
                         [guest.player_id])

    def test_observer_limit_and_disconnect_cleanup(self):
        server = self.room()
        host = self.joined(server, host_token=server.host_token)
        observers = [self.joined(server, role='spectator') for _ in range(16)]
        excess = self.client(server, role='spectator')
        self.error(excess, 'full')
        self.snapshot(host, lambda m: m['room']['spectators'] == 16)
        observers[0].close()
        self.snapshot(host, lambda m: m['room']['spectators'] == 15)
        replacement = self.joined(server, role='spectator')
        self.assertEqual(self.snapshot(replacement)['room']['spectators'], 16)

    def test_chat_history_is_latest_fifty_and_visible_to_late_join(self):
        server = self.room()
        host = self.joined(server, host_token=server.host_token)
        for i in range(55):
            host.send({'type': 'chat', 'message': 'message {}'.format(i)})
        snapshot = self.snapshot(host, lambda m: bool(m['room']['chat']) and
                                 m['room']['chat'][-1]['message'] == 'message 54')
        history = snapshot['room']['chat']
        self.assertEqual(len(history), 50)
        self.assertEqual(history[0]['message'], 'message 5')
        observer = self.joined(server, role='spectator')
        self.assertEqual(self.snapshot(observer)['room']['chat'], history)

    def test_safe_return_to_lobby_final_phase_pause_and_host_end_session(self):
        server, host, guest = self.two_players()
        host.send({'type': 'return_lobby'})
        self.error(host, 'finishes')
        self.research(host)
        self.research(guest)
        for actor in (host, guest):
            actor.send({'type': 'action', 'action': {'type': 'pass'}})
            self.snapshot(actor, lambda m, pid=actor.player_id: m['game']['last_actor'] == pid
                          and m['game']['revision'] >= 3)
        host.close()
        snapshot = self.snapshot(guest, lambda m: m['room']['paused'])
        self.assertEqual(snapshot['game']['phase'], 'final')
        host = self.joined(server, resume_token=host.resume_token)
        for actor in (host, guest):
            actor.send({'type': 'action', 'action': {'type': 'pass'}})
            self.snapshot(actor, lambda m, pid=actor.player_id: m['game']['last_actor'] == pid
                          and m['game']['revision'] >= 5)
        host.send({'type': 'return_lobby'})
        snapshot = self.snapshot(host, lambda m: not m['room']['started'])
        self.assertIsNone(snapshot['game'])
        self.assertTrue(all(not player['ready'] for player in snapshot['room']['players']))
        host.send({'type': 'end_session'})
        self.wait(guest, lambda m: m.get('type') == 'disconnected')
        server.close()
        self.assertFalse(server._thread.is_alive())
        self.assertFalse(server._peers)

    def test_close_is_idempotent_and_client_observes_server_shutdown(self):
        server = self.room()
        self.assertIs(server.start(), server)
        client = self.joined(server)
        server.close()
        server.close()
        self.wait(client, lambda m: m.get('type') == 'disconnected')
        client.close()
        client.close()
        self.assertFalse(client.connected)
        self.assertFalse(client._thread.is_alive())
        self.assertFalse(server._thread.is_alive())
        with self.assertRaises(OSError):
            client.send({'type': 'ready'})


class ProtocolTests(SocketCase):
    def test_frame_fragmentation_coalescing_unicode_and_exact_boundary(self):
        first = {'type': 'chat', 'message': '公会'}
        second = {'type': 'ready', 'ready': True}
        frame = network._encode(first)
        decoder = network._Decoder()
        self.assertEqual(list(decoder.feed(frame[:2])), [])
        self.assertEqual(list(decoder.feed(frame[2:7])), [])
        self.assertEqual(list(decoder.feed(frame[7:] + network._encode(second))), [first, second])
        overhead = len(network._encode({'data': ''})) - 4
        frame = network._encode({'data': 'x' * (network.MAX_FRAME_SIZE - overhead)})
        self.assertEqual(len(frame), network.MAX_FRAME_SIZE + 4)
        self.assertEqual(len(list(network._Decoder().feed(frame))), 1)
        with self.assertRaises(network.ProtocolError):
            network._encode({'data': 'x' * (network.MAX_FRAME_SIZE - overhead + 1)})

    def test_malformed_frames_do_not_kill_server(self):
        server = self.room()
        payloads = [b'[]', b'null', b'{broken', b'{"x":NaN}', b'{"x":Infinity}',
                    b'{"type":"join","type":"action"}', b'\xff', b'\x80\x04N.',
                    b'[' * 2000 + b']' * 2000]
        frames = [struct.pack('!I', len(p)) + p for p in payloads]
        frames += [struct.pack('!I', 0), struct.pack('!I', network.MAX_FRAME_SIZE + 1)]
        for frame in frames:
            with self.subTest(frame=frame[:30]):
                with socket.create_connection(('127.0.0.1', server.port), timeout=2) as sock:
                    sock.sendall(frame)
                    decoder = network._Decoder()
                    messages = []
                    while not messages:
                        data = sock.recv(65536)
                        self.assertTrue(data)
                        messages.extend(decoder.feed(data))
                    self.assertEqual(messages[0]['type'], 'error')
                    self.assertEqual(sock.recv(1), b'')
        healthy = self.joined(server)
        self.assertEqual(len(self.snapshot(healthy)['room']['players']), 1)

    def test_live_fragmented_join_and_coalesced_commands(self):
        server = self.room()
        with socket.create_connection(('127.0.0.1', server.port), timeout=2) as sock:
            frame = network._encode({'type': 'join', 'name': 'Manual'})
            for byte in frame[:7]:
                sock.sendall(bytes([byte]))
            sock.sendall(frame[7:] + network._encode({'type': 'ready'}) +
                         network._encode({'type': 'chat', 'message': 'hello'}))
            decoder = network._Decoder()
            messages = []
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                messages.extend(decoder.feed(sock.recv(65536)))
                snapshots = [m for m in messages if m['type'] == 'snapshot' and m['room']['chat']]
                if snapshots:
                    self.assertTrue(snapshots[-1]['room']['players'][0]['ready'])
                    self.assertTrue(any(m['type'] == 'welcome' for m in messages))
                    break
            else:
                self.fail('No snapshot after fragmented join.')

    def test_configuration_and_outbound_json_validation(self):
        self.assertIs(network.RoomClient, network.Client)
        for maximum in (0, 6, True, 2.5):
            with self.assertRaises(ValueError):
                network.RoomServer(max_players=maximum)
        for message in ([], {'value': float('nan')}, {'value': set()}, {'value': '\ud800'}):
            with self.assertRaises(network.ProtocolError):
                network._encode(message)


@unittest.skipUnless(importlib.util.find_spec('guild_engine'), 'guild_engine.py has not landed yet')
class RealEngineIntegrationTests(SocketCase):
    def two_players(self):
        server, host, guest = super().two_players()
        self.research_snapshots = {}
        for step in range(1,8):
            for client in (host,guest):
                client.send(dict(type='action',action=dict(type='draft_pick',draft_step=step,index=0)))
            for client in (host,guest):
                self.research_snapshots[client] = self.snapshot(client,lambda m:m['game'] and m['game'].get('draft_step',0)>step)
        return server, host, guest

    def test_undo_is_authorized_by_seat_and_invalidated_by_other_player(self):
        server, host, guest = self.two_players()
        first = self.research(host)
        second = self.research(guest)
        undo_id = second['game']['undo']['id']
        self.assertTrue(second['game']['undo']['available'])
        host.send(dict(type='action',action=dict(type='undo',undo_id=undo_id)))
        self.wait(host,lambda m:m.get('type')=='error')
        guest.send(dict(type='action',action=dict(type='undo',undo_id=undo_id)))
        restored = self.snapshot(guest,lambda m:m['game']['phase']=='research'
                                 and not m['game']['players'][guest.player_id]['researched'])
        self.assertFalse(restored['game']['undo']['available'])
        self.assertEqual(restored['game']['players'][guest.player_id]['offered_count'],8)
        second = self.research(guest)
        old = second['game']['undo']['id']
        royal = first['game']['players'][host.player_id]['achievements'][0]
        host.send(dict(type='action',action=dict(type='discard_achievement',id=royal)))
        changed = self.snapshot(guest,lambda m:m['game']['players'][host.player_id]['achievement_count']==1)
        self.assertFalse(changed['game']['undo']['available'])
        guest.send(dict(type='action',action=dict(type='undo',undo_id=old)))
        self.wait(guest,lambda m:m.get('type')=='error')

    def test_humans_start_research_late_observer_and_reconnect(self):
        server, host, guest = self.two_players()
        snapshot = self.research_snapshots[guest]
        self.assert_private(snapshot['game'], guest.player_id)
        self.research(host)
        self.assertEqual(self.research(guest)['game']['phase'], 'action')
        observer = self.joined(server, role='spectator')
        self.assert_private(self.snapshot(observer)['game'], None)
        token, pid = host.resume_token, host.player_id
        host.close()
        snapshot = self.snapshot(observer, lambda m: any(
            p['id'] == pid and not p['connected'] for p in m['room']['players']))
        self.assertTrue(all(not p['bot'] for p in snapshot['room']['players']))
        resumed = self.joined(server, resume_token=token)
        snapshot = self.snapshot(resumed)
        self.assertEqual(resumed.player_id, pid)
        self.assertTrue(resumed.is_host)
        self.assert_private(snapshot['game'], pid)


if __name__ == '__main__':
    unittest.main()
