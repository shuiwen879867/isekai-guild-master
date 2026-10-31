# -*- coding: utf-8 -*-
"""apply_phase_b_prologue2.py — 補齊冒險者的慶典擴充序章（序章-2，1欄×3列）。

順序：#15 藥師的侍從、#19 搶先召喚、#17 鍛造屋的見習生（依使用者提供）。
"""
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(os.path.dirname(ROOT), 'GuildMaster-Godot-src')
PACK = os.path.join(os.path.dirname(ROOT), '圖包')
ART = os.path.join(ROOT, 'art')
RULES = os.path.join(ROOT, 'rules')
SHEET = '序章-2(冒險者的慶典擴充).png'
COLS, ROWS = 1, 3
STORY_CELLS = {15: 1, 19: 2, 17: 3}


def convert():
    from PIL import Image
    src = os.path.join(PACK, SHEET)
    dst = os.path.join(ART, 'images', 'tts', 'packxg2.webp')
    if os.path.isfile(dst):
        print('webp exists')
        return
    im = Image.open(src).convert('RGB')
    im.save(dst, 'WEBP', quality=92, method=4)
    print('converted:', dst, im.size, '%.1f MB' % (os.path.getsize(dst) / 1048576))


def atlas_and_catalog():
    from PIL import Image
    cp = os.path.join(SRC, 'data', 'catalog.json')
    cat = json.load(io.open(cp, encoding='utf-8'))
    atlas = cat['atlas']
    W, H = Image.open(os.path.join(PACK, SHEET)).size
    cw, ch = W / COLS, H / ROWS
    for cell in range(1, COLS * ROWS + 1):
        ri, ci = divmod(cell - 1, COLS)
        x0, y0 = int(round(ci * cw)), int(round(ri * ch))
        x1, y1 = int(round((ci + 1) * cw)), int(round((ri + 1) * ch))
        atlas['pack/XG2_%d' % cell] = {'path': 'images/tts/packxg2.webp',
                                       'box': [x0, y0, x1 - x0, y1 - y0]}
    for pid, cell in STORY_CELLS.items():
        it = cat['prologues'].get(str(pid))
        if it is not None:
            it['source'] = 'pack/XG2_%d' % cell
    json.dump(cat, io.open(cp, 'w', encoding='utf-8', newline=''), ensure_ascii=False, separators=(',', ':'))
    print('catalog: XG2 keys +', COLS * ROWS, '| prologues wired:', len(STORY_CELLS))


def patch_rules():
    p = os.path.join(RULES, 'guild_card_corrections.py')
    s = io.open(p, encoding='utf-8').read()
    if 'Phase B2（2026-10' in s:
        print('rules already patched')
        return
    anchor = "    QUESTS[24]['name'] = '\u4e8c\u661f\u4ee5\u4e0a\u677f\u57571'\n"
    assert s.count(anchor) == 1, 'anchor missing'
    block = ("    # Phase B2（2026-10）：冒險者的慶典擴充序章改純掃描面（pack/XG2_<格>）\n"
             "    _story_cells2 = %r\n"
             "    for _pid, _cell in _story_cells2.items():\n"
             "        if _pid in PROLOGUES:\n"
             "            PROLOGUES[_pid]['source'] = 'pack/XG2_%%d' %% _cell\n" % STORY_CELLS)
    s = s.replace(anchor, anchor + block)
    io.open(p, 'w', encoding='utf-8', newline='').write(s)
    print('rules: patched')


if __name__ == '__main__':
    convert()
    atlas_and_catalog()
    patch_rules()
    import sys
    sys.path.insert(0, RULES)
    import guild_content
    import guild_new_content
    for pid in (15, 19, 17):
        it = guild_new_content.PROLOGUES[pid]
        print('prologue', pid, it['name'], '→', it['source'])
