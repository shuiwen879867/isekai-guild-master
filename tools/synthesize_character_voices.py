"""Resumeable synthesis and offline Vorbis conversion of the authored cues."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'qa/voice-runtime'))
import edge_tts
import imageio_ffmpeg
from mutagen.oggvorbis import OggVorbis


def hidden():
    if os.name != 'nt':return None
    value=subprocess.STARTUPINFO();value.dwFlags|=subprocess.STARTF_USESHOWWINDOW;value.wShowWindow=0
    return value


def convert(source, destination):
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=destination.with_name(destination.stem+'.incoming.ogg')
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-nostdin','-v','error','-y','-i',str(source),'-vn','-ac','1','-ar','44100','-af','loudnorm=I=-18:TP=-2:LRA=7','-c:a','libvorbis','-q:a','4',str(temporary)],capture_output=True,check=True,timeout=35,startupinfo=hidden())
    duration=OggVorbis(temporary).info.length
    if not .6<duration<25:raise RuntimeError('Unexpected speech duration: '+str(destination))
    temporary.replace(destination)
    return duration


async def run(args):
    manifest=json.loads((ROOT/'GuildMaster-Godot-src/data/voice_manifest.json').read_text('utf8'))
    clips=[(path,info) for path,info in manifest['clips'].items() if info['source']=='synthetic']
    if args.limit:clips=clips[:args.limit]
    cache=ROOT/'qa/tts-cache';cache.mkdir(exist_ok=True)
    semaphore=asyncio.Semaphore(args.workers)
    complete=0;failed=[];started=time.time()
    async def one(path,info):
        nonlocal complete
        async with semaphore:
            signature=hashlib.sha256(json.dumps(info,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
            source=cache/(signature+'.mp3');metadata=cache/(signature+'.jsonl')
            destination=ROOT/'GuildMaster-Godot-src'/path
            receipt=cache/(signature+'.receipt.json')
            if receipt.exists() and destination.is_file():
                saved=json.loads(receipt.read_text('utf8'))
                if saved['sha256']==hashlib.sha256(destination.read_bytes()).hexdigest():
                    complete+=1;return
            for attempt in range(5):
                try:
                    if not source.exists() or source.stat().st_size<1500:
                        temporary=source.with_suffix('.incoming.mp3')
                        stream=edge_tts.Communicate(info['text'],info['speaker'],rate=info['rate'],pitch=info['pitch'],proxy=args.proxy,receive_timeout=45)
                        await asyncio.wait_for(stream.save(str(temporary),str(metadata)),timeout=65)
                        temporary.replace(source)
                    duration=await asyncio.to_thread(convert,source,destination)
                    receipt.write_text(json.dumps(dict(path=path,sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),duration=duration,text=info['text'],speaker=info['speaker'],rate=info['rate'],pitch=info['pitch']),ensure_ascii=False,indent=2),'utf8')
                    complete+=1
                    if complete%10==0 or complete==len(clips):
                        progress=dict(complete=complete,total=len(clips),failed=len(failed),elapsed_seconds=round(time.time()-started),last_character=info['character'])
                        (ROOT/'qa/tts-progress.json').write_text(json.dumps(progress,ensure_ascii=False),'utf8')
                        print(json.dumps(progress,ensure_ascii=False),flush=True)
                    await asyncio.sleep(.12)
                    return
                except Exception as error:
                    if attempt==4:
                        failed.append(dict(path=path,error=type(error).__name__+': '+str(error)[:180]))
                        print('VOICE_FAILED '+path+' '+type(error).__name__,flush=True)
                    else:await asyncio.sleep(1.5*(attempt+1))
    await asyncio.gather(*(one(path,info) for path,info in clips))
    result=dict(complete=complete,total=len(clips),failed=failed,elapsed_seconds=round(time.time()-started))
    (ROOT/'qa/tts-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps(result,ensure_ascii=False),flush=True)
    if failed:raise SystemExit(1)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--proxy',default=os.environ.get('VOICE_PROXY'))
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--limit',type=int,default=0)
    asyncio.run(run(parser.parse_args()))
