"""Deploy with Python 3.9+; no display, Ren'Py, pip packages or game images needed."""
import argparse
import json
import logging
import signal
import threading
from pathlib import Path

from guild_lobby import LobbyServer
from guild_replay import ReplayStore, ReplayWeb
from guild_site import SiteWeb

# Built-in fallbacks; server_config.json overrides them, command-line flags override both.
DEFAULTS = {
    'host': '0.0.0.0',
    'game_port': 6677,
    'replay_port': 6767,
    'site_port': 6680,
    'record_replays': True,
    'enable_replay': True,
    'enable_site': True,
}
PORT_KEYS = ('game_port', 'replay_port', 'site_port')
FLAG_KEYS = ('record_replays', 'enable_replay', 'enable_site')


def load_config(path):
    """Read server_config.json. Unknown keys are ignored and bad values fall back."""
    config = {}
    file = Path(path)
    if not file.is_file():
        logging.warning('找不到配置文件 %s，使用内置默认设置。', file)
        return config
    try:
        # utf-8-sig also accepts plain UTF-8, while tolerating the BOM that
        # Notepad and PowerShell add when saving JSON on Windows.
        raw = json.loads(file.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as exc:
        logging.warning('配置文件 %s 无法解析（%s），使用内置默认设置。', file, exc)
        return config
    if not isinstance(raw, dict):
        logging.warning('配置文件 %s 必须是 JSON 对象，使用内置默认设置。', file)
        return config
    host = raw.get('host')
    if isinstance(host, str) and host.strip():
        config['host'] = host.strip()
    elif host is not None:
        logging.warning('host 必须是非空字符串，已忽略：%r', host)
    for key in PORT_KEYS:
        value = raw.get(key)
        if value is None:
            continue
        if type(value) is int and 0 <= value <= 65535:
            config[key] = value
        else:
            logging.warning('%s 必须是 0-65535 的整数，已忽略：%r', key, value)
    for key in FLAG_KEYS:
        value = raw.get(key)
        if value is None:
            continue
        if isinstance(value, bool):
            config[key] = value
        else:
            logging.warning('%s 必须是 true 或 false，已忽略：%r', key, value)
    return config


def main():
    parser = argparse.ArgumentParser(description='Isekai Guild Master multiplayer server')
    here = Path(__file__).resolve().parent
    parser.add_argument('--config', default=str(here / 'server_config.json'),
                        help='JSON config file; command-line flags override it')
    parser.add_argument('--host', default=None, help='listen address (config: host)')
    parser.add_argument('--port', type=int, default=None, help='game port (config: game_port)')
    parser.add_argument('--web-port', type=int, default=None, help='replay website port (config: replay_port)')
    parser.add_argument('--site-port', type=int, default=None, help='matchmaking website port (config: site_port)')
    parser.add_argument('--no-replay', action='store_true', help='do not start the replay website')
    parser.add_argument('--no-site', action='store_true', help='do not start the matchmaking website')
    parser.add_argument('--no-record', action='store_true', help='do not write replay files to disk')
    parser.add_argument('--replay-dir', default=None, help='where replay files live (default: ./replays)')
    parser.add_argument('--site-dir', default=None, help='matchmaking website folder (default: ./site)')
    parser.add_argument('--download-dir', default=None, help='client download folder (default: ./downloads)')
    parser.add_argument('--max-rooms', type=int, default=None)
    parser.add_argument('--idle-hours', type=float, default=24,
                        help='Deprecated compatibility option; started empty rooms now use their disconnect grace before cleanup.')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

    settings = dict(DEFAULTS)
    settings.update(load_config(args.config))
    host = args.host or settings['host']
    game_port = settings['game_port'] if args.port is None else args.port
    replay_port = settings['replay_port'] if args.web_port is None else args.web_port
    site_port = settings['site_port'] if args.site_port is None else args.site_port
    record = settings['record_replays'] and not args.no_record
    enable_replay = settings['enable_replay'] and not args.no_replay
    enable_site = settings['enable_site'] and not args.no_site
    replay_dir = args.replay_dir or str(here / 'replays')
    site_dir = args.site_dir or str(here / 'site')
    download_dir = args.download_dir or str(here / 'downloads')
    max_rooms = 32 if args.max_rooms is None else args.max_rooms

    stop = threading.Event()
    def shutdown(*_):
        stop.set()
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    # The store always exists so an enabled replay website can serve existing files;
    # `record` decides whether this run appends new steps to it.
    store = ReplayStore(replay_dir)
    if record:
        store.recover()
    web = ReplayWeb(store, host, replay_port) if enable_replay else None
    site = None
    server = None
    try:
        server = LobbyServer(host, game_port, max_rooms, args.idle_hours,
                             replay_store=store if record else None).start()
        if enable_site:
            site = SiteWeb(site_dir, download_dir, host, site_port,
                           portrait_dir=here / 'replay_web' / 'portraits',
                           overrides={'game_port': game_port, 'replay_port': replay_port,
                                      'site_port': site_port, 'replay_enabled': bool(web)},
                           status_provider=server.public_status)
    except Exception:
        if server:
            server.close()
        if web:
            web.close()
        if site:
            site.close()
        raise
    if web:
        web.start()
    if site:
        site.start()
    logging.info('Guild server listening on %s:%s', host, server.port)
    logging.info('Replay website %s', ('listening on %s:%s' % (host, web.port)) if web else 'disabled')
    logging.info('Matchmaking website %s', ('listening on %s:%s' % (host, site.port)) if site else 'disabled')
    logging.info('Replay recording %s (folder: %s)', 'enabled' if record else 'disabled', replay_dir)
    try:
        while not stop.wait(1):
            if server._stop.is_set():
                raise RuntimeError('Server network loop stopped unexpectedly')
    finally:
        server.close()
        if record:
            for room in list(server.rooms.values()):
                store.finish(room.replay_id)
        if web:
            web.close()
        if site:
            site.close()
        logging.info('Guild server stopped; transient rooms discarded')


if __name__ == '__main__':
    main()
