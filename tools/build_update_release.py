"""Export and package the complete 4.1 client and independent Python server."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'GuildMaster-Godot-src';PACK=ROOT/'GuildMaster-Godot';SERVER=ROOT/'guild-server'
from release_config import VERSION,REVISION


def export_fingerprint():
    digest=hashlib.sha256()
    paths=[p for p in files(SRC) if p.suffix in ('.gd','.tscn') or p.parent==SRC/'data' or p.name in ('project.godot','export_presets.cfg')]
    paths.extend([ROOT/'docs/VOICE_VALIDATION.json',ROOT/'release.json'])
    for path in sorted(paths):
        digest.update(path.relative_to(ROOT).as_posix().encode());digest.update(path.read_bytes())
    return digest.hexdigest()

def files(folder):
    for path in sorted(folder.rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts or '.godot' in path.parts:continue
        if path.name=='.gdignore' or path.suffix in ('.pyc','.pyo','.import'):continue
        yield path

def manifest(folder):
    data=dict(version=VERSION,revision=REVISION,upstream='cat90132-beep/isekai-guild-master@refactor',
              files={p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files(folder) if p.name!='BUILD_INFO.json' and not any(k in p.relative_to(folder).parts for k in ('tools','replays','downloads','replay-cache'))})
    voice=json.loads((ROOT/'docs/VOICE_VALIDATION.json').read_text('utf8'))
    data['voice_validation']={k:v for k,v in voice.items() if k!='files'}
    (folder/'BUILD_INFO.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),'utf8')

def package(folder,target):
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in files(folder):
            if any(k in path.relative_to(folder).parts for k in ('tools','replays','downloads','replay-cache')):continue
            archive.write(path,folder.name+'/'+path.relative_to(folder).as_posix())
    with zipfile.ZipFile(target) as archive:assert archive.testzip() is None
    return dict(name=target.name,size_bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest())

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--skip-export',action='store_true');parser.add_argument('--server-only',action='store_true');args=parser.parse_args()
    from validate_voice_assets import validate
    validate()
    export_receipt=ROOT/'qa/export-voice-build.json'
    if args.skip_export or args.server_only:
        if not export_receipt.exists():raise SystemExit('Export a client with complete bilingual voices before reusing it.')
        saved=json.loads(export_receipt.read_text('utf8'))
        if saved['source_fingerprint']!=export_fingerprint() or saved['pck_sha256']!=hashlib.sha256((PACK/'GuildMaster.pck').read_bytes()).hexdigest():
            raise SystemExit('The exported client is stale; run a full build with bilingual voice export.')
    subprocess.run([sys.executable,str(ROOT/'tools/prepare_update.py')],check=True)
    # Keep source-tree F5 testing identical to the exported local engine.
    for path in (PACK/'rules').glob('*.py'):shutil.copy2(path,SRC/'rules'/path.name)
    editor=Path(os.environ.get('GODOT_BIN',ROOT.parent/'.qa-runtime/godot-sdk/editor/Godot_v4.7.2-stable_win64_console.exe'))
    template=ROOT.parent/'.qa-runtime/godot-sdk/templates/windows_release_x86_64.exe'
    if not args.skip_export and not args.server_only:
        if not editor.is_file():raise SystemExit('Set GODOT_BIN to the Godot 4.7.2 console executable.')
        preset=(SRC/'export_presets.cfg').read_text('utf8')
        preset=preset.replace('name="GuildMaster"','name="Windows"').replace('runnable=false','runnable=true')
        preset=re.sub(r'export_path="[^"]*"','export_path="../GuildMaster-Godot/GuildMaster.exe"',preset)
        preset=preset.replace('exclude_filter="art/*, rules/*, ui/bottons/*, reference/*"','exclude_filter="art/*,rules/*,runtime/*,tools/*,data/qa-*.json,data/demo.json,reference/*"')
        if template.exists():preset=re.sub(r'custom_template/release="[^"]*"','custom_template/release="'+Path(os.path.relpath(template,SRC)).as_posix()+'"',preset)
        (SRC/'export_presets.cfg').write_text(preset,'utf8')
        env=os.environ.copy();env['APPDATA']=str(ROOT/'qa/build-appdata');env['LOCALAPPDATA']=str(ROOT/'qa/build-localappdata')
        for key in ('APPDATA','LOCALAPPDATA'):Path(env[key]).mkdir(parents=True,exist_ok=True)
        with (ROOT/'qa/export.log').open('w',encoding='utf8') as log:
            result=subprocess.run([str(editor),'--headless','--path',str(SRC),'--export-release','Windows',str(PACK/'GuildMaster.exe')],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
        report=(ROOT/'qa/export.log').read_text('utf8')
        errors=[line for line in report.splitlines() if 'SCRIPT ERROR' in line or 'ERROR:' in line and 'root certificate' not in line]
        if result.returncode or errors:raise SystemExit('\n'.join(errors[-20:]) or report[-2000:])
        export_receipt.write_text(json.dumps(dict(source_fingerprint=export_fingerprint(),pck_sha256=hashlib.sha256((PACK/'GuildMaster.pck').read_bytes()).hexdigest()),indent=2),'utf8')
    (PACK/'docs').mkdir(exist_ok=True)
    for name in ['DLC玩法总览.png','更新日志_4.1.png']:shutil.copy2(ROOT/'docs'/name,PACK/'docs'/name)
    for folder in (PACK,SERVER):
        (folder/'docs').mkdir(exist_ok=True)
        for name in ['CHARACTER_VOICES.json','VOICE_VALIDATION.json','SUPPLIED_VOICE_OVERRIDES.json','PORTRAIT_STATUS.json']:
            shutil.copy2(ROOT/'docs'/name,folder/'docs'/name)
    shutil.copy2(ROOT/'README.md',PACK/'README.md')
    # Public replay thumbnails and website documentation use the new prints.
    sys.path.insert(0,str(SERVER))
    from guild_content import HEROES,CARDS
    import guild_card_layouts
    # The upstream server index references original glyph/paper atlases but
    # did not ship them. Standalone installs must have all 516 components.
    for name in guild_card_layouts.component_paths():
        relative=Path(name.removeprefix('images/'));destination=SERVER/relative
        if not destination.is_file():
            candidates=[ROOT.parent/name,PACK/'art'/relative]
            source=next((p for p in candidates if p.is_file()),None)
            if source is None:raise SystemExit('Missing required replay component: '+name)
            destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,destination)
    # Preserve the same scan faces used by the client for cards that are not
    # covered by the legacy component index.
    catalog=json.loads((SRC/'data/catalog.json').read_text('utf8'))
    def raster(source):
        atlas=catalog['atlas'].get(source)
        if atlas:
            im=raster(atlas['path']);x,y,w,h=map(int,atlas['box']);return im.crop((x,y,x+w,y+h))
        path=PACK/'art'/source
        if not path.is_file():path=PACK/'art'/source.removeprefix('images/')
        return Image.open(path).convert('RGB')
    from guild_content import ACHIEVEMENTS
    images={}
    for definition in list(catalog['cards'].values())+list(catalog['achievements'].values()):
        if definition.get('available',True) and type(definition.get('image')) is int:images[definition['image']]=definition
    for definition in list(CARDS.values())+list(ACHIEVEMENTS.values()):
        number=definition.get('image')
        if not definition.get('available',True) or type(number)is not int:continue
        if number not in (53,65,77,83) and guild_card_layouts.source_for_image(number) in guild_card_layouts.LAYOUTS:continue
        full=SERVER/'replay_web/cardfull'/(str(number)+'.jpg')
        if full.is_file():continue
        im=raster(images[number]['source'])
        for folder,width in [('cardfull',1200),('cards',240)]:
            face=im.copy();face.thumbnail((width,width));face.save(SERVER/'replay_web'/folder/(str(number)+'.jpg'),quality=90)
    for key,hero in HEROES.items():
        if not hero.get('screenshot_print'):continue
        for number,source in zip(hero['images'],hero['source']):
            image=Image.open(PACK/'art'/source).convert('RGB')
            for folder,width in [('cardfull',1000),('cards',240)]:
                output=SERVER/'replay_web'/folder;output.mkdir(parents=True,exist_ok=True)
                face=image.copy();face.thumbnail((width,width));face.save(output/(str(number)+'.jpg'),quality=90)

    portraits=json.loads((SRC/'data/portraits.json').read_text('utf8'))['sources']
    for key,source in portraits.items():
        output=SERVER/'replay_web/portraits'/(key+'.png')
        if not source:
            if output.is_file():output.unlink()
            continue
        portrait=raster(source).convert('RGBA');portrait.thumbnail((210,320));portrait.save(output)
    for folder,width in [('cardfull',800),('cards',240)]:
        im=Image.open(PACK/'art/supplied/lazy_life.webp').convert('RGB');im.thumbnail((width,width));im.save(SERVER/'replay_web'/folder/'303.jpg',quality=90)
    shots=SERVER/'site/shots';shots.mkdir(exist_ok=True)
    for source,name in [('DLC玩法总览.png','dlc-guide-4.1.png'),('更新日志_4.1.png','update-4.1.png')]:shutil.copy2(ROOT/'docs'/source,shots/name)
    config=SERVER/'site/site.json';data=json.loads(config.read_text('utf8'));data['version']=VERSION;config.write_text(json.dumps(data,ensure_ascii=False,indent=2),'utf8')
    for folder in ([SERVER] if args.server_only else [PACK,SERVER]):manifest(folder)
    dist=ROOT/'dist';dist.mkdir(exist_ok=True)
    client=next(a for a in json.loads((ROOT/'release-files.json').read_text('utf8'))['artifacts'] if a['name']==f'GuildMaster-Windows-{VERSION}.zip') if args.server_only else package(PACK,dist/f'GuildMaster-Windows-{VERSION}.zip')
    artifacts=[client,package(SERVER,dist/f'guild-server-{VERSION}.zip')]
    (ROOT/'release-files.json').write_text(json.dumps(dict(version=VERSION,revision=REVISION,artifacts=artifacts),ensure_ascii=False,indent=2),'utf8')
    print(json.dumps(artifacts,indent=2))

if __name__=='__main__':main()
