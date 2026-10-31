"""Apply a prepared server archive on Linux with an idle check and rollback.

Run over authenticated, pinned SSH. This program never manages other services.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def command(*args):return subprocess.run(args,check=True,capture_output=True,text=True,timeout=30).stdout.strip()
def status():
    with urllib.request.urlopen('http://127.0.0.1:6680/api/status',timeout=8) as response:return json.load(response)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',type=Path,required=True);parser.add_argument('--sha256',required=True)
    parser.add_argument('--client-validation',type=Path,required=True)
    parser.add_argument('--production',type=Path,default=Path('/srv/guanpeng/received_files/guild-server'))
    args=parser.parse_args();production=args.production.resolve();archive=args.archive.resolve();stage=archive.parent
    if str(production)!='/srv/guanpeng/received_files/guild-server':raise RuntimeError('Unexpected production directory')
    stage.relative_to(Path('/srv/guanpeng-maintenance'))
    if digest(archive)!=args.sha256:raise RuntimeError('Uploaded archive hash mismatch')
    if shutil.disk_usage('/').free < archive.stat().st_size*6:raise RuntimeError('Insufficient space for stage and rollback')
    incoming=stage/'incoming';incoming.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as package:
        for entry in package.infolist():
            path=(incoming/entry.filename).resolve();path.relative_to(incoming.resolve())
            if not entry.filename.startswith('guild-server/'):raise RuntimeError('Unexpected archive member')
        package.extractall(incoming)
    source=incoming/'guild-server'
    info=json.loads((source/'BUILD_INFO.json').read_text('utf8'))
    voices=info.get('voice_validation',{})
    if not voices.get('passed') or voices.get('hero_versions')!=57 or voices.get('characters')!=25 or voices.get('clips')!=1134 or voices.get('default_voice_language')!='ja' or voices.get('languages')!={'ja':567,'zh_CN':567}:
        raise RuntimeError('Full character voice validation is required before deployment')
    client_check=json.loads(args.client_validation.read_text('utf8'))
    if not client_check.get('passed') or not client_check.get('package_passed') or client_check.get('clips')!=1134 or client_check.get('manifest_sha256')!=voices.get('manifest_sha256') or set(client_check.get('languages',[]))!={'ja','zh_CN'}:
        raise RuntimeError('The matching exported bilingual client must pass before deployment')
    command(sys.executable,'-m','compileall','-q',str(source))
    check=status()
    if check.get('active_room_count') or check.get('connected_people'):raise RuntimeError('Server is in use; deployment deferred')
    config=production/'server_config.json';config_hash=digest(config) if config.exists() else None
    backup=stage/'previous';backup.mkdir(exist_ok=True)
    plan=[]
    for path in sorted(source.rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts:continue
        relative=path.relative_to(source)
        if relative.parts[0] in ('replays','downloads') or str(relative)=='server_config.json':continue
        destination=(production/relative).resolve();destination.relative_to(production)
        if destination.exists() and digest(destination)==digest(path):continue
        previous=None
        if destination.exists():
            st=destination.stat();previous=dict(mode=st.st_mode&0o777,uid=st.st_uid,gid=st.st_gid)
            old=backup/relative;old.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(destination,old)
        plan.append(dict(path=relative.as_posix(),previous=previous))
    (stage/'plan.json').write_text(json.dumps(plan,indent=2),'utf8')
    account=pwd.getpwnam('guanpeng');stopped=False
    try:
        # Re-check immediately before the short stop, after backing up files.
        if status().get('connected_people') or status().get('active_room_count'):raise RuntimeError('New connection arrived; deployment deferred')
        command('systemctl','stop','guanpeng-guild.service');stopped=True
        for item in plan:
            relative=Path(item['path']);destination=production/relative
            destination.parent.mkdir(parents=True,exist_ok=True)
            temp=destination.with_name(destination.name+'.guild-update-incoming')
            shutil.copyfile(source/relative,temp);os.chmod(temp,0o644);os.chown(temp,account.pw_uid,account.pw_gid);os.replace(temp,destination)
        command(sys.executable,'-m','compileall','-q',str(production))
        command('systemctl','start','guanpeng-guild.service')
        online=None
        for unused in range(20):
            try:
                online=status()
                if online.get('online'):break
            except OSError:pass
            time.sleep(.5)
        if not online or not online.get('online'):raise RuntimeError('Updated server did not become ready')
        for path in ('/shots/update-4.1.png','/shots/dlc-guide-4.1.png','/assets/hero/bell_revised_black.png'):
            with urllib.request.urlopen('http://127.0.0.1:6680'+path,timeout=10) as response:
                if response.status!=200 or not response.read(8):raise RuntimeError('Missing updated web asset')
        probe="import guild_engine,guild_network,json; from guild_content import HEROES; c=guild_network.Client('127.0.0.1',6677,'ReleaseProbe',lobby=True).connect(); c.close(); print(json.dumps({'module':guild_engine.__file__,'version':guild_network.CLIENT_VERSION,'heroes':len(HEROES)}))"
        result=json.loads(subprocess.run([sys.executable,'-c',probe],cwd=production,capture_output=True,text=True,check=True,timeout=20).stdout)
        if result['version']!='4.1.0' or Path(result['module']).parent!=production:raise RuntimeError('Production module identity mismatch')
        if config_hash and digest(config)!=config_hash:raise RuntimeError('Server configuration changed')
        for path in source.glob('*.py'):
            if digest(path)!=digest(production/path.name):raise RuntimeError('Production rule hash mismatch')
        receipt=dict(status='deployed',version='4.1.0',revision='20261031-4.1.0-refactor-update',backup=str(backup),
                     changed_files=len(plan),config_preserved=True,replays_preserved=True,rules_match_package=True,
                     archive_sha256=args.sha256,voice_validation=voices,
                     active=command('systemctl','is-active','guanpeng-guild.service'),main_pid=command('systemctl','show','guanpeng-guild.service','-p','MainPID','--value'),probe=result)
        (stage/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),'utf8');print(json.dumps(receipt,ensure_ascii=False))
    except BaseException:
        if stopped:
            command('systemctl','stop','guanpeng-guild.service')
            for item in plan:
                destination=(production/item['path']).resolve();destination.relative_to(production)
                previous=item['previous']
                if previous:
                    shutil.copy2(backup/item['path'],destination);os.chmod(destination,previous['mode']);os.chown(destination,previous['uid'],previous['gid'])
                elif destination.is_file():destination.unlink()
            command('systemctl','start','guanpeng-guild.service')
        raise

if __name__=='__main__':main()
