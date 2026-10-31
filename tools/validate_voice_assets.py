"""Fail closed when any playable print, cue or validated audio file is missing."""
import argparse
import array
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'GuildMaster-Godot-src'
MANIFEST=SOURCE/'data/voice_manifest.json'
REPORT=ROOT/'docs/VOICE_VALIDATION.json'
EVENTS={'intro','select','rank_1','rank_2','rank_3','close-first','close-last','close-shop','settle-win','settle-lose'}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(require_report=True):
    sys.path.insert(0,str(ROOT/'guild-server'))
    from guild_content import HEROES
    manifest=json.loads(MANIFEST.read_text('utf8'))
    if set(manifest['heroes'])!=set(HEROES):raise RuntimeError('Voice coverage does not match the playable hero catalog')
    required=set()
    for hero,definition in manifest['heroes'].items():
        if definition['name']!=HEROES[hero]['name']:raise RuntimeError('Incorrect voice identity: '+hero)
        if set(definition['events'])!={'ja','zh_CN'}:raise RuntimeError('Incomplete voice languages: '+hero)
        for locale,events in definition['events'].items():
            if set(events)!=EVENTS:raise RuntimeError('Incomplete voice events: '+hero+'/'+locale)
            for paths in events.values():
                if not paths:raise RuntimeError('Empty voice event: '+hero+'/'+locale)
                required.update(paths)
    if manifest['default_locale']!='ja':raise RuntimeError('Japanese must be the default voice language')
    if set(manifest['clips'])!=required:raise RuntimeError('Audio index and event mappings differ')
    for name in sorted(required):
        path=(SOURCE/name).resolve();path.relative_to((SOURCE/'audio/voice').resolve())
        if not path.is_file():raise RuntimeError('Missing character audio: '+name)
        data=path.read_bytes()
        if not data.startswith(b'OggS') or b'vorbis' not in data[:100] or len(data)<1500:
            raise RuntimeError('Audio is not a valid Vorbis asset: '+name)
    if require_report:
        report=json.loads(REPORT.read_text('utf8'))
        if not report['passed'] or report['manifest_sha256']!=sha(MANIFEST) or set(report['files'])!=required:
            raise RuntimeError('Voice validation is missing or stale; decode all assets again')
        for name,entry in report['files'].items():
            if entry['sha256']!=sha(SOURCE/name):raise RuntimeError('Audio changed after validation: '+name)
    return manifest


def decode_one(name):
    import imageio_ffmpeg
    startup=None
    if os.name=='nt':
        startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    path=SOURCE/name
    result=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-nostdin','-v','error','-i',str(path),'-f','s16le','-ac','1','-ar','16000','pipe:1'],capture_output=True,check=True,timeout=25,startupinfo=startup)
    pcm=array.array('h');pcm.frombytes(result.stdout)
    duration=len(pcm)/16000
    if not .5<duration<45:raise RuntimeError('Unexpected decoded duration: '+name)
    rms=math.sqrt(sum(value*value for value in pcm)/len(pcm))/32768
    audible=sum(abs(value)>328 for value in pcm)/16000
    if rms<.002 or audible<.15:raise RuntimeError('Silent or incomplete speech: '+name)
    return name,dict(sha256=sha(path),duration_seconds=round(duration,3),rms_db=round(20*math.log10(rms),2),audible_seconds=round(audible,3),size_bytes=path.stat().st_size)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--decode',action='store_true');args=parser.parse_args()
    manifest=validate(require_report=not args.decode)
    if args.decode:
        with ThreadPoolExecutor(max_workers=4) as pool:files=dict(pool.map(decode_one,sorted(manifest['clips'])))
        languages={locale:len({p for h in manifest['heroes'].values() for paths in h['events'][locale].values() for p in paths}) for locale in manifest['locales']}
        report=dict(passed=True,manifest_sha256=sha(MANIFEST),characters=len(manifest['characters']),hero_versions=len(manifest['heroes']),clips=len(files),languages=languages,default_voice_language=manifest['default_locale'],synthetic_clips=sum(c['source']=='synthetic' for c in manifest['clips'].values()),supplied_clips=sum(c['source']=='supplied_recording' for c in manifest['clips'].values()),total_seconds=round(sum(f['duration_seconds'] for f in files.values()),2),files=files)
        REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    else:report=json.loads(REPORT.read_text('utf8'))
    print(json.dumps({k:v for k,v in report.items() if k!='files'},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
