# -*- coding: utf-8 -*-
"""apply_phase_b_prologue.py — 序章卡改為純掃描（序章-1.png，7×3）。

對應（卡面 PRO 碼 → catalog prologue id → 格子）：
  0→15, 1→9, 2→12, 3→2, 4→11, 5→10, 6→1, 8→8, 9→14,
  10→3, 12→6, 13→4, 16→5, 18→7, 20→13
缺少掃描的序章（暫留原狀）：15 藥師的侍從、17 鍛造屋的見習生、19 搶先召喚
"""
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(os.path.dirname(ROOT), 'GuildMaster-Godot-src')
PACK = os.path.join(os.path.dirname(ROOT), '圖包')
ART = os.path.join(ROOT, 'art')
RULES = os.path.join(ROOT, 'rules')

STORY_CELLS = {0: 15, 1: 9, 2: 12, 3: 2, 4: 11, 5: 10, 6: 1, 8: 8, 9: 14,
               10: 3, 12: 6, 13: 4, 16: 5, 18: 7, 20: 13}


def convert_sheet():
    from PIL import Image
    src = os.path.join(PACK, '序章-1.png')
    dst = os.path.join(ART, 'images', 'tts', 'packxg.webp')
    if os.path.isfile(dst):
        print('webp exists:', dst)
        return
    im = Image.open(src).convert('RGB')
    im.save(dst, 'WEBP', quality=92, method=4)
    print('converted:', dst, im.size, '%.1f MB' % (os.path.getsize(dst) / 1048576))


def add_atlas():
    cp = os.path.join(SRC, 'data', 'catalog.json')
    cat = json.load(io.open(cp, encoding='utf-8'))
    atlas = cat['atlas']
    from PIL import Image
    im = Image.open(os.path.join(PACK, '序章-1.png'))
    W, H = im.size
    cols, rows = 7, 3
    cw, ch = W / cols, H / rows
    for cell in range(1, cols * rows + 1):
        ri, ci = divmod(cell - 1, cols)
        x0, y0 = int(round(ci * cw)), int(round(ri * ch))
        x1, y1 = int(round((ci + 1) * cw)), int(round((ri + 1) * ch))
        atlas['pack/XG_%d' % cell] = {'path': 'images/tts/packxg.webp',
                                      'box': [x0, y0, x1 - x0, y1 - y0]}
    for pid, cell in STORY_CELLS.items():
        it = cat['prologues'].get(str(pid))
        if it is not None:
            it['source'] = 'pack/XG_%d' % cell
    json.dump(cat, io.open(cp, 'w', encoding='utf-8', newline=''), ensure_ascii=False, separators=(',', ':'))
    print('catalog: atlas XG keys +', cols * rows, '| prologues wired:', len(STORY_CELLS))


def patch_rules():
    p = os.path.join(RULES, 'guild_card_corrections.py')
    s = io.open(p, encoding='utf-8').read()
    if 'Phase B（2026-10' in s:
        print('rules already patched')
        return
    anchor = "    from guild_new_content import QUESTS, PROLOGUES\n"
    assert s.count(anchor) == 1, 'anchor missing'
    block = anchor + (
        "    # Phase B（2026-10）：序章卡改用純掃描面（pack/XG_<格>）\n"
        "    _story_cells = %r\n"
        "    for _pid, _cell in _story_cells.items():\n"
        "        if _pid in PROLOGUES:\n"
        "            PROLOGUES[_pid]['source'] = 'pack/XG_%%d' %% _cell\n" % STORY_CELLS)
    s = s.replace(anchor, block)
    io.open(p, 'w', encoding='utf-8', newline='').write(s)
    print('rules: prologue sources patched')


if __name__ == '__main__':
    convert_sheet()
    add_atlas()
    patch_rules()
    import sys
    sys.path.insert(0, RULES)
    import guild_content
    P = guild_content.PROLOGUES
    for pid in (0, 3, 6, 20, 15, 17, 19):
        print('prologue', pid, P[pid]['name'], '→', P[pid]['source'])
