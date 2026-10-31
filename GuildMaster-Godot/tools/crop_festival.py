# -*- coding: utf-8 -*-
"""Crop festival expansion card scans (320-338) from TTS packs for player review."""
import json, os, re, sys
from PIL import Image

CATALOG = r'..\GuildMaster-Godot-src\data\catalog.json'
ART_DIR = r'..\GuildMaster-Godot-src\art'
OUT_DIR = sys.argv[1]
os.makedirs(OUT_DIR, exist_ok=True)

with open(CATALOG, encoding='utf-8') as f:
    cat = json.load(f)
atlas = cat['atlas']

def resolve_source(path):
    # 'images/tts/pack15.webp' style under art/
    return os.path.join(ART_DIR, path.replace('/', os.sep))

for cid in range(320, 339):
    c = cat['cards'][str(cid)]
    ip = c.get('image_path', '')
    src = None
    if ip.startswith('tts_128_') and ip in atlas:
        info = atlas[ip]
        src = resolve_source(info['path'])
        box = info['box']
    elif re.match(r'pack/(\d+)_(\d+)$', ip):
        m = re.match(r'pack/(\d+)_(\d+)$', ip)
        # find or reuse atlas entries for that pack page, else raw guess 640x460 grid
        page = int(m.group(1)); idx = int(m.group(2))
        for k, v in atlas.items():
            if re.match(r'pack/\d+_(\d+)$', k) and k == ip:
                info = v
                src = resolve_source(info['path'])
                box = info['box']
                break
        else:
            # search atlas by path containing packN and matching index boxes ordered
            print('card', cid, 'fallback manual box needed for', ip)
            continue
    else:
        print('card', cid, 'unknown image_path', ip)
        continue
    im = Image.open(src).crop((box[0], box[1], box[0] + box[2], box[1] + box[3]))
    out = os.path.join(OUT_DIR, '%d.png' % cid)
    im.save(out)
    print('card', cid, '->', out, im.size)
print('done')
