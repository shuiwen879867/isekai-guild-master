# -*- coding: utf-8 -*-
"""make_card_reference.py — 產出單一整合的「卡片 ↔ 卡面 ↔ 功能」對照表。

輸出（GuildMaster-Godot-src/）：
  card_reference.csv   給人看（Excel 可開）
  card_reference.json  完整結構（含卡面來源、atlas 裁切框、變體、序章、委託、引擎同步檢查）
  CARD_DATA_GUIDE.md   資料導覽：哪個檔案管什麼、怎麼改
"""
import csv
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(os.path.dirname(ROOT), 'GuildMaster-Godot-src')

SYNC_FIELDS = ('price', 'gold', 'gold_pro', 'strength', 'str_pro', 'pot', 'civ', 'point', 'draw')


def engine_cards():
    sys.path.insert(0, os.path.join(ROOT, 'rules'))
    import guild_content
    return guild_content.CARDS


def describe_face(cat, key):
    """回傳 (來源檔, 格框, 型別)；key 可能是 atlas 鍵或直接檔名"""
    if not key:
        return ('', '', 'none')
    entry = cat['atlas'].get(key)
    if entry:
        return (entry.get('path', ''), entry.get('box', ''), 'atlas-cell')
    return (key, '', 'whole-file')


def main():
    cat = json.load(io.open(os.path.join(SRC, 'data', 'catalog.json'), encoding='utf-8'))
    engine = engine_cards()

    rows = []
    detail = []
    for cid, c in sorted(cat['cards'].items(), key=lambda kv: int(kv[0])):
        ip = c.get('image_path') or ''
        src_file, box, kind = describe_face(cat, ip)
        variants = c.get('face_variants') or {}
        eng = engine.get(int(cid), {})
        diff = []
        for f in SYNC_FIELDS:
            a = c.get(f)
            b = eng.get(f)
            if a != b and not (a in (None, 0) and b in (None, 0)):
                diff.append('%s:%s≠%s' % (f, a, b))
        note = ''
        if c.get('available') is False:
            note = '停用'
        if c.get('archived_print'):
            note = (note + ';舊印刷' if note else '舊印刷')
        if c.get('special'):
            note = (note + ';special' if note else 'special')
        row = {
            'id': cid,
            'printed_code': c.get('printed_code') or '',
            'name': c.get('name') or '',
            'kind': c.get('kind') or '',
            'price': c.get('price'),
            'available': c.get('available'),
            'face_key': ip,
            'face_file': src_file,
            'cell_box': json.dumps(box, ensure_ascii=False) if box else '',
            'face_kind': kind,
            'variants': '; '.join('%s=%s' % (k, v) for k, v in sorted(variants.items())),
            'tags': ','.join(c.get('tags') or []),
            'ui_summary': c.get('ui_summary') or '',
            'note': note,
            'engine_diff': '; '.join(diff),
        }
        rows.append(row)
        detail.append({'card': c, 'face': {'key': ip, 'file': src_file, 'box': box, 'kind': kind},
                       'engine_diff': diff})

    # 序章 / 委託
    prologues = []
    for pid, it in sorted(cat.get('prologues', {}).items(), key=lambda kv: int(kv[0])):
        f, box, kind = describe_face(cat, it.get('source', ''))
        prologues.append({'id': int(pid), 'name': it.get('name'), 'source': it.get('source'),
                          'face_file': f, 'box': box})
    quests = []
    for qid, it in sorted(cat.get('quests', {}).items(), key=lambda kv: int(kv[0])):
        f, box, kind = describe_face(cat, it.get('source', ''))
        quests.append({'id': int(qid), 'name': it.get('name'), 'source': it.get('source'),
                       'face_file': f, 'box': box})

    # CSV（写入 reference/，已加 .gdignore，避免被 Godot 当翻译资源打包）
    ref_dir = os.path.join(SRC, 'reference')
    os.makedirs(ref_dir, exist_ok=True)
    csv_path = os.path.join(ref_dir, 'card_reference.csv')
    fields = ['id', 'printed_code', 'name', 'kind', 'price', 'available', 'face_key', 'face_file',
              'cell_box', 'face_kind', 'variants', 'tags', 'ui_summary', 'note', 'engine_diff']
    with io.open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # JSON
    json_path = os.path.join(ref_dir, 'card_reference.json')
    json.dump({'generated_at': __import__('datetime').date.today().isoformat(),
               'cards': detail, 'prologues': prologues, 'quests': quests},
              io.open(json_path, 'w', encoding='utf-8', newline=''), ensure_ascii=False, indent=1)

    # Guide
    guide = '''# 卡片資料導覽（現行）

## 一、看「卡片 ↔ 卡面 ↔ 功能」的整合表
- `card_reference.csv`：每張卡一列（卡號、卡名、費用、卡面鍵、來源檔、格框、變體面、能力摘要、備註、與引擎數值差異）
- `card_reference.json`：同一批資料的完整結構（含 atlas 裁切框、序章、委託）

## 二、各檔案職責
| 檔案 | 作用 |
|---|---|
| `data/catalog.json`（src） | **客戶端卡表**：卡片名稱/費用/卡面 `image_path`/`ui_summary`＋`atlas` 裁切表。遊戲執行時讀的是 **pck 內打包的同一份**，改完需重建 pck |
| `data/card_layouts.json`（src） | 原生字體版面（僅少數未改掃描面的條目還在用） |
| `rules/guild_content.py` 等 | **規則引擎**（離線/連線權威）：卡片效果、費用、可用性。以簡體卡名為鍵 |
| `rules/guild_card_corrections.py` | 校正補丁層（Phase A/B 的城市卡重啟、序章掃描面、E-025 等都在這） |
| `rules/guild_new_events.py` | 祭典事件（#320-337）定義 |
| `rules/guild_new_art.py` | 圖面/修正版群組與資產對應 |
| `rules/guild_asset_manifest.json` | 原資產清單（已移除 185/187/216/217） |
| `art/images/tts/pack*.webp` | 你的掃描拼圖；`atlas` 的 `pack/<片>_<格>` 從這裡裁切 |
| `art/images/new_art/*.webp` | 原單卡掃描（E 族、Z-001、A-042-EX1 等） |

## 三、卡面如何決定
1. 卡片有 `image_path = pack/<片>_<格>` → 從 `art/images/tts/pack<片>.webp` 依 `atlas` 的 box 裁切，整張繪製。
2. `face_variants`（solo）＝單人替換面；已啟用顯示：`GuildArtStore.card_face()` 在 `mode == "solo"` 時改取 `face_variants.solo`（`main.gd _process` 依 `game.options.solo` 同步 `store.mode`）。變體卡（variable_labyrinth / variable_tiles）資料僅供引擎 DLC 判定，未在 UI 切換。引擎端同時以 `rules/guild_mode_variants.py` 於開局時套用對應模式的效果與 image 欄位。
3. 序章：`prologues[].source` 指向 `pack/XG_*`、`pack/XG2_*`。
4. 委託（目標卡）：`quests[].source` 指向 `tts_5_*`（005.webp，已隨包附帶）。

## 四、現行已知狀態
- 219 張卡面＝掃描拼圖（pack1..14、9B、XG、XG2）
- #229 A-042 保留 `new_art/847012`（即 A-042-EX1 印面）
- #206-214（A-109~A-117）已重啟並改新印面；#327 費用 20
- 祭典卡 11 張（#320/321/322/323/325/326/328/331/333/335/336）面檔 `tts/128.webp` 缺 → 目前無圖
- Z-002（聖女的遺痕）＝`tts_27_28`（027.webp）
- 185/187（英雄卡 3×7）與 216/217（單人王權卡 3×2）的程式碼必須保留：
  rules/guild_new_heroes.py 與 guild_new_content.py 匯入時會用 manifest 尺寸計算來源；
  圖檔缺 → 該批卡面空白，補上掃描檔即可自動恢復（atlas 鍵已重建）

## 五、重建提醒
遊戲內的卡面與數值要**重建 pck** 後才生效；`rules/`（離線引擎）為磁碟即時生效。
'''
    guide_path = os.path.join(ref_dir, 'CARD_DATA_GUIDE.md')
    io.open(guide_path, 'w', encoding='utf-8', newline='').write(guide)

    print('rows:', len(rows), '| prologues:', len(prologues), '| quests:', len(quests))
    print('wrote:', csv_path)
    print('wrote:', json_path)
    print('wrote:', guide_path)
    diff_n = sum(1 for r in rows if r['engine_diff'])
    print('engine_diff rows:', diff_n)
    for r in rows[:3]:
        print(' sample:', {k: r[k] for k in ('id', 'printed_code', 'name', 'face_key', 'face_file')})


if __name__ == '__main__':
    main()
