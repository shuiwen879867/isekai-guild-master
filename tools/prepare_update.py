"""Prepare the refactor source, external runtime, synchronized rules and catalog."""
from pathlib import Path
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'GuildMaster-Godot-src';PACK=ROOT/'GuildMaster-Godot';SERVER=ROOT/'guild-server'

def main():
    previous=ROOT.parent/'.godot-client'
    for name in ('python.exe','pythonw.exe','python313.zip'):
        destination=PACK/'runtime'/name
        if not destination.exists():shutil.copy2(previous/'runtime'/name,destination)
    if not (SRC/'main.tscn').exists():shutil.copy2(previous/'main.tscn',SRC/'main.tscn')
    for path in SERVER.glob('*.py'):shutil.copy2(path,PACK/'rules'/path.name)
    sys.path.insert(0,str(SERVER))
    from guild_content import HEROES,CHARACTERS,CARDS
    path=SRC/'data/catalog.json';catalog=json.loads(path.read_text('utf8'))
    for section,definitions in [('heroes',HEROES),('cards',CARDS)]:
        for key,definition in definitions.items():
            key=str(key)
            if key not in catalog[section]:catalog[section][key]=definition
            else:
                saved={k:v for k,v in catalog[section][key].items() if k in ('source','portrait','image_path','face_variants','printed_text','name')}
                catalog[section][key].update(definition);catalog[section][key].update(saved)
                if key.startswith('shion'):catalog[section][key]['name']='紫苑'
    catalog['characters']=CHARACTERS
    path.write_text(json.dumps(catalog,ensure_ascii=False,separators=(',',':')),'utf8')
    for folder in ('art','runtime','rules'):
        if not (SRC/folder).exists():shutil.copytree(PACK/folder,SRC/folder)
    print('Prepared',len(HEROES),'hero prints in',len(CHARACTERS),'character groups.')

if __name__=='__main__':main()
