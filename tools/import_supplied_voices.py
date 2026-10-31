"""Replace only matching Japanese cues; retain every unmatched asset exactly."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import html
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'GuildMaster-Godot-src'
IDS={'alicia':1,'melissa':2,'misha':3,'sofia':4,'bai':5,'hainie':6,'ayaka':7,'skadi':8,'peria':9,'shion':10,'elu':11,'siren':12,'ruby':13,'saphia':13}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def read_script(path):
    characters={};current=None
    for line in path.read_text('utf-8-sig').splitlines():
        heading=re.match(r'^## (kanban-\d+)\s+(.+)',line)
        if heading:
            current=heading.group(1);characters[current]=dict(name=heading.group(2),slots={})
        elif current and line.startswith('| `'):
            columns=[v.strip() for v in line.strip().strip('|').split('|')]
            slot=columns[0].strip('`')
            if not re.fullmatch(r'(?:select\.(?:intro|white|red)\.v[12]|card\.(?:white|red)\.r[123]|(?:close\.(?:shop|first|last)|settle\.(?:win|lose))\.v[12])',slot):continue
            text=columns[3] if slot.startswith('card.') else columns[2]
            characters[current]['slots'][slot]=html.unescape(re.sub(r'<[^>]+>',' ',text))
    return characters

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',type=Path,default=Path('C:/Users/react/Downloads/ogg.rar'));parser.add_argument('--script',type=Path,default=Path('C:/Users/react/Downloads/台本审核.md'));args=parser.parse_args()
    work=ROOT/'qa/provided-ogg';work.mkdir(exist_ok=True)
    listing=subprocess.run(['C:/Program Files/7-Zip/7z.exe','l','-slt','-ba','-sccUTF-8',str(args.archive)],capture_output=True,text=True,encoding='utf8',check=True).stdout
    members=[]
    for block in listing.split('\n\n'):
        values=dict(line.split(' = ',1) for line in block.splitlines() if ' = ' in line)
        if not values or values.get('Folder')=='+' or values.get('Attributes','').startswith('D'):continue
        path=PureWindowsPath(values['Path'])
        if path.is_absolute() or '..' in path.parts or len(path.parts)!=2 or path.parts[0]!='ogg' or not re.fullmatch(r'kanban-\d{3}__[a-z0-9-]+\.ogg',path.name):raise RuntimeError('Unexpected archive path: '+str(path))
        members.append(path.name)
    if len(members)!=len(set(members)):raise RuntimeError('Duplicate audio archive members')
    extracted=work/'extracted'
    subprocess.run(['C:/Program Files/7-Zip/7z.exe','x','-y','-aoa','-o'+str(extracted),str(args.archive)],capture_output=True,check=True)
    script=read_script(args.script)
    manifest=json.loads((SOURCE/'data/voice_manifest.json').read_text('utf8'))
    before={path:sha(SOURCE/path) for path in manifest['clips']}
    replacements={};missing=[]
    for hero,definition in manifest['heroes'].items():
        character=definition['character']
        if character not in IDS:continue
        identifier='kanban-%03d'%IDS[character]
        for event,targets in definition['events']['ja'].items():
            for index,target in enumerate(targets,1):
                suffix=('card-'+definition['variant']+'-r'+event.removeprefix('rank_')) if event.startswith('rank_') else ('select-intro' if event=='intro' else 'select-'+definition['variant'] if event=='select' else event)+'-v'+str(index)
                name=identifier+'__'+suffix+'.ogg'
                slot=suffix.replace('-','.')
                if name not in members:
                    missing.append(dict(member=name,target=target,retained_sha256=before[target]));continue
                if slot not in script[identifier]['slots']:raise RuntimeError('Audio is not covered by the supplied script: '+name)
                reference=script[identifier]['slots'][slot]
                normalize=lambda text:re.sub(r'[\W_]+','',text)
                first=script[identifier]['slots']['card.'+definition['variant']+'.r1']
                includes_first=event=='select' and len(normalize(first))>4 and normalize(reference).startswith(normalize(first))
                replacements[target]=dict(member=name,identifier=identifier,slot=slot,reference_text_zh_TW=reference,includes_rank_one=includes_first,character=character,event=manifest['clips'][target]['event'],source='supplied_recording',archive='ogg.rar',source_sha256=sha(extracted/'ogg'/name))
    converted=work/'vorbis';converted.mkdir(exist_ok=True)
    unique=sorted({value['member'] for value in replacements.values()})
    import imageio_ffmpeg
    from mutagen.oggvorbis import OggVorbis
    startup=None
    if os.name=='nt':
        startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    def convert(name):
        original=extracted/'ogg'/name;destination=converted/name
        if b'vorbis' in original.read_bytes()[:100]:shutil.copy2(original,destination)
        else:subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-nostdin','-v','error','-y','-i',str(original),'-c:a','libvorbis','-q:a','5',str(destination)],capture_output=True,check=True,timeout=40,startupinfo=startup)
        if not .5<OggVorbis(destination).info.length<45:raise RuntimeError('Unexpected recording duration: '+name)
    with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(convert,unique))
    same_shion={}
    sample=Path('C:/Users/react/Downloads/kanban-010__settle-win-v2.zip')
    if sample.is_file():
        with zipfile.ZipFile(sample) as archive:
            same_shion={name:archive.read(name)==(extracted/'ogg'/name).read_bytes() for name in unique if name.startswith('kanban-010__')}
    backup=work/'prior';changed=0
    for target,info in replacements.items():
        destination=SOURCE/target;saved=backup/target
        if not saved.exists():saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(destination,saved)
        if not same_shion.get(info['member'],False):
            shutil.copy2(converted/info['member'],destination)
        info['sha256']=sha(destination)
        if info['sha256']!=before[target]:changed+=1
    untouched={target:expected for target,expected in before.items() if target not in replacements}
    for target,expected in untouched.items():
        if sha(SOURCE/target)!=expected:raise RuntimeError('Unmatched audio changed: '+target)
    record=dict(archive='ogg.rar',archive_sha256=sha(args.archive),script='台本审核.md',script_sha256=sha(args.script),language='ja',source_recordings=len(unique),mapped_assets=len(replacements),changed_assets=changed,clips=replacements,missing_retained=list({entry['member']:entry for entry in missing}.values()),unmatched_assets_sha256=untouched)
    (ROOT/'docs/SUPPLIED_VOICE_OVERRIDES.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n','utf8')
    subprocess.run([sys.executable,str(ROOT/'tools/prepare_character_voices.py')],check=True)
    print(json.dumps({k:v for k,v in record.items() if k not in ('clips','unmatched_assets_sha256')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
