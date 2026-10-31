"""Restore the exact pre-4.1 game files while preserving configuration and replays."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request

PRODUCTION = Path('/srv/guanpeng/received_files/guild-server')
STAGE = Path('/srv/guanpeng-maintenance/guild-4.1-20261031-97e84bd')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=30).stdout.strip()


def api(suffix):
    with urllib.request.urlopen('http://127.0.0.1:6680/api/' + suffix, timeout=8) as response:
        return json.load(response)


def idle():
    value = api('status')
    if value.get('connected_people') or value.get('active_room_count'):
        raise RuntimeError('A game or player is online; restoration deferred')


def preserved_data():
    paths = [PRODUCTION / 'server_config.json']
    paths.extend(p for p in (PRODUCTION / 'replays').rglob('*') if p.is_file())
    return {p.relative_to(PRODUCTION).as_posix(): digest(p) for p in paths}


def replace(source, destination, metadata):
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + '.guild-restore-incoming')
    shutil.copy2(source, temporary)
    os.chmod(temporary, metadata['mode'])
    os.chown(temporary, metadata['uid'], metadata['gid'])
    os.replace(temporary, destination)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    production = PRODUCTION.resolve()
    if str(production) != str(PRODUCTION) or str(STAGE.resolve()) != str(STAGE):
        raise RuntimeError('Unexpected server or backup path')
    plan = json.loads((STAGE / 'plan.json').read_text('utf8'))
    backup = STAGE / 'previous'
    incoming = STAGE / 'incoming/guild-server'
    for item in plan:
        relative = Path(item['path'])
        destination = (production / relative).resolve()
        destination.relative_to(production)
        if relative.parts[0] in ('replays', 'downloads') or relative.as_posix() == 'server_config.json':
            raise RuntimeError('The deployment plan unexpectedly includes persistent data')
        if not destination.is_file() or digest(destination) != digest(incoming / relative):
            raise RuntimeError('Production changed since deployment: ' + str(relative))
        if item['previous']:
            previous = (backup / relative).resolve()
            previous.relative_to(backup.resolve())
            if not previous.is_file():
                raise RuntimeError('Missing previous file: ' + str(relative))
            if previous.suffix == '.py':
                compile(previous.read_bytes(), str(previous), 'exec')
    expected_version = '3.2.0'
    if "CLIENT_VERSION = '3.2.0'" not in (backup / 'guild_network.py').read_text('utf8'):
        raise RuntimeError('The backup is not the expected old server')
    idle()
    protected = preserved_data()
    if not args.apply:
        print(json.dumps(dict(status='ready',version=expected_version,files=len(plan),persistent_files=len(protected))))
        return
    forward = STAGE / 'before-restore-4.1'
    forward.mkdir(exist_ok=True)
    metadata = {}
    for item in plan:
        relative = Path(item['path'])
        source = production / relative
        saved = forward / relative
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, saved)
        stat = source.stat()
        metadata[item['path']] = dict(mode=stat.st_mode & 0o777, uid=stat.st_uid, gid=stat.st_gid)
    idle()
    stopped = False
    try:
        command('systemctl', 'stop', 'guanpeng-guild.service')
        stopped = True
        for item in plan:
            destination = production / item['path']
            if item['previous']:
                replace(backup / item['path'], destination, item['previous'])
            else:
                destination.unlink()
        command('systemctl', 'start', 'guanpeng-guild.service')
        online = None
        for unused in range(30):
            try:
                online = api('status')
                if online.get('online') and api('site').get('version') == expected_version:
                    break
            except OSError:
                pass
            time.sleep(.5)
        if not online or not online.get('online') or api('site').get('version') != expected_version:
            raise RuntimeError('Restored server failed its health check')
        probe = "import guild_network,json; c=guild_network.Client('127.0.0.1',6677,'RestoreHealth',lobby=True).connect(); c.close(); print(json.dumps({'version':guild_network.CLIENT_VERSION,'module':guild_network.__file__}))"
        result = json.loads(subprocess.run([sys.executable, '-c', probe], cwd=production, capture_output=True, text=True, check=True, timeout=20).stdout)
        if result['version'] != expected_version:
            raise RuntimeError('Restored TCP protocol mismatch')
        for item in plan:
            path = production / item['path']
            if item['previous']:
                if digest(path) != digest(backup / item['path']):
                    raise RuntimeError('Restored file mismatch: ' + item['path'])
            elif path.exists():
                raise RuntimeError('New-version file was not removed: ' + item['path'])
        if protected != preserved_data():
            raise RuntimeError('Configuration or replay data changed')
        receipt = dict(status='restored',version=expected_version,reason='Full character voice coverage is not ready; user requested the old server until completion',restored_files=sum(bool(i['previous']) for i in plan),removed_new_files=sum(not bool(i['previous']) for i in plan),config_preserved=True,replays_preserved=True,persistent_files_verified=len(protected),active=command('systemctl','is-active','guanpeng-guild.service'),probe=result,backup=str(backup),forward_backup=str(forward))
        (STAGE / 'restore-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),'utf8')
        print(json.dumps(receipt,ensure_ascii=False,indent=2))
    except BaseException:
        if stopped:
            command('systemctl','stop','guanpeng-guild.service')
            for item in plan:
                replace(forward / item['path'], production / item['path'], metadata[item['path']])
            command('systemctl','start','guanpeng-guild.service')
        raise


if __name__ == '__main__':
    main()
