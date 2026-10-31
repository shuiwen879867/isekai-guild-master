# -*- coding: utf-8 -*-
"""wire_festival_v2.py — 慶典擴充新牌面（卡牌-15/16 PNG）接線。

卡牌-15（5×2）：A-118,A-119,A-120,A-121,A-123 / A-124,A-126,A-127,A-128
卡牌-16（5×2）：B-026,B-027,B-028,D-014,D-015 / D-016,E-026
（A-122/A-125 維持卡牌-12 的 A-X01/A-X02 勘誤面；E-025 維持 pack/11_1）
"""
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(os.path.dirname(ROOT), 'GuildMaster-Godot-src')
PACK = os.path.join(os.path.dirname(ROOT), '圖包')
ART = os.path.join(ROOT, 'art')
COLS, ROWS = 5, 2

NAME15 = '卡牌-15(冒險者的慶典擴充).png'
NAME16 = '卡牌-16(冒險者的慶典擴充).png'

# id → (sheet, cell 1..10)
WIRE = {
    320: ('15', 1), 321: ('15', 2), 322: ('15', 3), 323: ('15', 4), 325: ('15', 5),
    326: ('15', 6), 328: ('15', 7), 329: ('15', 8), 330: ('15', 9),
    331: ('16', 1), 332: ('16', 2), 333: ('16', 3), 334: ('16', 4), 335: ('16', 5),
    336: ('16', 6), 338: ('16', 7),
}
UNUSED_KEYS = ['tts_128_4', 'tts_128_7', 'tts_128_17']


def convert():
    from PIL import Image
    for name, tag in ((NAME15, 'pack15.webp'), (NAME16, 'pack16.webp')):
        src = os.path.join(PACK, name)
        dst = os.path.join(ART, 'images', 'tts', tag)
        im = Image.open(src).convert('RGB')
        im.save(dst, 'WEBP', quality=92, method=4)
        print('converted:', tag, im.size, '%.1fMB' % (os.path.getsize(dst) / 1048576))


def wire():
    from PIL import Image
    cp = os.path.join(SRC, 'data', 'catalog.json')
    cat = json.load(io.open(cp, encoding='utf-8'))
    atlas = cat['atlas']
    dims = {}
    for name, num in ((NAME15, '15'), (NAME16, '16')):
        dims[num] = Image.open(os.path.join(PACK, name)).size
    for cid, (sheet, cell) in WIRE.items():
        w, h = dims[sheet]
        idx = cell - 1
        row, col = divmod(idx, COLS)
        box = [int(w * col / COLS), int(h * row / ROWS),
               int(w * (col + 1) / COLS) - int(w * col / COLS),
               int(h * (row + 1) / ROWS) - int(h * row / ROWS)]
        atlas['tts_128_%d' % (cid - 320)] = {
            'path': 'images/tts/pack%s.webp' % sheet, 'box': box}
    removed = 0
    for k in UNUSED_KEYS:
        if k in atlas:
            atlas.pop(k); removed += 1
    # #334 卡名依新印面
    if '334' in cat['cards']:
        cat['cards']['334']['name'] = 'Phrase百貨'
    json.dump(cat, io.open(cp, 'w', encoding='utf-8', newline=''), ensure_ascii=False, separators=(',', ':'))
    print('atlas wired:', len(WIRE), '| removed unused:', removed)

    # 規則端：#334 卡名
    ep = os.path.join(ROOT, 'rules', 'guild_new_events.py')
    s = io.open(ep, encoding='utf-8').read()
    s2 = s.replace("E(14,'巨大建筑物百货'", "E(14,'Phrase百货'")
    if s2 != s:
        io.open(ep, 'w', encoding='utf-8', newline='').write(s2)
        print('rules: #334 renamed Phrase百货')


if __name__ == '__main__':
    convert()
    wire()
    import sys
    sys.path.insert(0, os.path.join(ROOT, 'rules'))
    import guild_content
    C = guild_content.CARDS
    print('engine OK. #334 name:', C[334]['name'])
    cat = json.load(io.open(os.path.join(SRC, 'data', 'catalog.json'), encoding='utf-8'))
    for cid, (sheet, cell) in sorted(WIRE.items()):
        key = 'tts_128_%d' % (cid - 320)
        print(' #%-4d %-16s → %s' % (cid, cat['cards'][str(cid)]['name'], cat['atlas'][key]))
