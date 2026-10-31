#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""apply_phase_a.py — 把 Phase A 的「格↔卡」對照套進資料。

輸入：pack_review/map_result.json（map_pack_faces.py 產出）
輸出（--apply 時）：
  1. 圖包拼圖轉成 art/images/tts/pack01..packNN.webp
  2. catalog.json 新增 atlas 鍵 pack/<tag>_<cell>（含精確 box）
  3. 卡片 image_path/source 指向該鍵（CardFace 由整張圖繪製）
     例外：#229 A-042 保留 847012（A-042-EX1 面）、#324/#327 指向 pack/12_x
  4. #206-214：available=True、special=False、指向 pack/12_2..12_10
  5. 9B 變體面 → card['face_variants']（solo / variable_labyrinth / variable_tiles）
  6. #327 費用 10→20（catalog + rules/guild_new_events.py）

用法：python tools/apply_phase_a.py [--apply]
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORT_ROOT = os.path.dirname(HERE)
SRC = os.path.join(os.path.dirname(EXPORT_ROOT), "GuildMaster-Godot-src")
PACK = os.path.join(os.path.dirname(EXPORT_ROOT), "圖包")
ART = os.path.join(EXPORT_ROOT, "art")
REVIEW = os.path.join(os.environ.get("TEMP", "."), "opencode", "pack_review")
RULES = os.path.join(EXPORT_ROOT, "rules")

# 圖包檔案 → 目標 tag
SHEET_FILES = [
    ("1", "卡牌-1.png"), ("2", "卡牌-2.png"), ("3", "卡牌-3.png"), ("4", "卡牌-4.png"),
    ("5", "卡牌-5.png"), ("6", "卡牌-6.png"), ("7", "卡牌-7.png"), ("8", "卡牌-8.png"),
    ("9B", "卡牌-9(B面,擴).png"), ("10", "卡牌-10.png"), ("11", "卡牌-11.png"),
    ("12", "卡牌-12.png"), ("13", "卡牌-13.png"), ("14", "卡牌-14.png"),
    ("XG", "序章-1.png"),
]
# 9B 記號分類（依角標圖確認）
VARIANT_MAP = {
    "E-007": ("solo", 1), "B-017": ("solo", 2), "D-002": ("solo", 3), "E-001": ("solo", 4),
    "E-015": ("variable_labyrinth", 5), "A-071": ("variable_labyrinth", 6),
    "A-080": ("variable_labyrinth", 7), "A-083": ("variable_labyrinth", 8),
    "A-088": ("variable_labyrinth", 9), "A-092": ("variable_labyrinth", 10),
    "A-095": ("variable_labyrinth", 11), "E-012": ("variable_labyrinth", 12),
    "A-042-EX1": ("errata", 13), "A-042": ("variable_tiles", 14),
}
SPECIAL_FACES = {  # printed_code → tag/cell（直接用 卡牌-12 的格子）
    "A-109": ("12", 2), "A-110": ("12", 3), "A-111": ("12", 4), "A-112": ("12", 5),
    "A-113": ("12", 6), "A-114": ("12", 7), "A-115": ("12", 8), "A-116": ("12", 9),
    "A-117": ("12", 10), "A-X02": ("12", 1), "A-X01": ("12", 11),
}
KEEP_FACE_CODES = {"A-042"}  # 保留現行 847012（A-042-EX1 面）


def fname_to_webp(tag):
    return "pack%s.webp" % tag.lower()


def run(apply=False):
    cat_path = os.path.join(SRC, "data", "catalog.json")
    cat = json.load(open(cat_path, encoding="utf-8"))
    atlas = cat.setdefault("atlas", {})
    map_result = json.load(open(os.path.join(REVIEW, "map_result.json"), encoding="utf-8"))

    # ---- 1. 掃描 map_result：建立 code → (tag, cell, box) ----
    code_cell = {}
    for fname, sh in map_result.items():
        tag = sh["tag"]
        if tag == "XG":
            continue
        for c in sh["cells"]:
            if c.get("empty") or c.get("back") or not c.get("card"):
                continue
            code = c["card"]["code"]
            if not code:
                continue
            if tag == "9B":
                continue
            # 直接匹配優先（序列填補者次之）
            prev = code_cell.get(code)
            if prev and (prev[3] and not c.get("filled_by_sequence")):
                code_cell[code] = (tag, c["cell"], c["box"], c.get("filled_by_sequence", False))
            elif not prev:
                code_cell[code] = (tag, c["cell"], c["box"], c.get("filled_by_sequence", False))

    # 9B 變體格
    variant_cell = {}
    for fname, sh in map_result.items():
        if sh["tag"] != "9B":
            continue
        for c in sh["cells"]:
            if c.get("card") and c["cell"] in [x[1] for x in VARIANT_MAP.values()]:
                variant_cell[c["cell"]] = c

    # ---- 2. 轉檔（或檢查）----
    os.makedirs(os.path.join(ART, "images", "tts"), exist_ok=True)
    todo_files = []
    for tag, fname in SHEET_FILES:
        if tag == "XG":
            continue  # 序章面本階段不入庫（序章顯示走原生版面）
        src = os.path.join(PACK, fname)
        dst = os.path.join(ART, "images", "tts", fname_to_webp(tag))
        todo_files.append((tag, src, dst))
    converted = 0
    for tag, src, dst in todo_files:
        if os.path.isfile(dst):
            continue
        if not os.path.isfile(src):
            print("[missing-pack]", src)
            continue
        if apply:
            from PIL import Image
            im = Image.open(src).convert("RGB")
            im.save(dst, "WEBP", quality=92, method=4)
            converted += 1

    # ---- 3. atlas 鍵 ----
    added_keys = 0
    for fname, sh in map_result.items():
        tag = sh["tag"]
        if tag == "XG":
            continue
        for c in sh["cells"]:
            if c.get("empty"):
                continue
            key = "pack/%s_%d" % (tag, c["cell"])
            x0, y0, x1, y1 = c["box"]
            atlas[key] = {"path": "images/tts/" + fname_to_webp(tag),
                          "box": [x0, y0, x1 - x0, y1 - y0]}
            added_keys += 1

    # ---- 4. 卡片 image_path 切換 ----
    changed = 0
    unmapped = []
    for cid, card in cat["cards"].items():
        code = card.get("printed_code") or ""
        if not code:
            continue
        if code in KEEP_FACE_CODES:
            continue
        if code in SPECIAL_FACES:
            tag, cell = SPECIAL_FACES[code]
            key = "pack/%s_%d" % (tag, cell)
        else:
            hit = code_cell.get(code)
            if not hit:
                unmapped.append((cid, code, card.get("name")))
                continue
            key = "pack/%s_%d" % (hit[0], hit[1])
        changed += 1
        if apply:
            card["image_path"] = key
            card["source"] = key
            card["new_art"] = True

    # ---- 5. #206-214 重啟 ----
    reenabled = []
    for cid, card in cat["cards"].items():
        code = card.get("printed_code") or ""
        if code in ("A-109", "A-110", "A-111", "A-112", "A-113", "A-114", "A-115", "A-116", "A-117"):
            tag, cell = SPECIAL_FACES[code]
            key = "pack/%s_%d" % (tag, cell)
            reenabled.append((cid, code, card.get("name")))
            if apply:
                card["available"] = True
                card["special"] = False
                card["archived_print"] = False
                card["unavailable_reason"] = ""
                card["image_path"] = key
                card["source"] = key
                card["new_art"] = True

    # ---- 6. #324/#327 面 + #327 費用 ----
    for cid, card in cat["cards"].items():
        code = card.get("printed_code") or ""
        name = card.get("name") or ""
        if name == "侵占救援物資":
            if apply:
                card["image_path"] = "pack/12_11"
                card["source"] = "pack/12_11"
                card["new_art"] = True
        if name == "魔獸的生態調查":
            if apply:
                card["image_path"] = "pack/12_1"
                card["source"] = "pack/12_1"
                card["new_art"] = True
                card["price"] = 20
                card["ui_summary"] = (card.get("ui_summary") or "").replace("费用10金币", "费用20金币")

    # ---- 7. face_variants ----
    variants_added = 0
    for cid, card in cat["cards"].items():
        code = card.get("printed_code") or ""
        spec = VARIANT_MAP.get(code)
        if not spec:
            continue
        mode, cell = spec
        variants_added += 1
        if apply:
            card.setdefault("face_variants", {})[mode] = "pack/9B_%d" % cell

    # ---- 8. rules 側：#327 費用 ----
    rules_changed = []
    new_events = os.path.join(RULES, "guild_new_events.py")
    if os.path.isfile(new_events):
        s = open(new_events, encoding="utf-8").read()
        m = re.search(r"E\(7,'(?:魔獸的生態調查|魔兽的生态调查)',\s*(\d+)", s)
        if m and m.group(1) != "20":
            s2 = s[:m.start(1)] + "20" + s[m.end(1):]
            if apply:
                open(new_events, "w", encoding="utf-8", newline="").write(s2)
            rules_changed.append("guild_new_events.py: E(7) price %s→20" % m.group(1))

    # ---- 9. 寫回 catalog ----
    if apply:
        open(cat_path, "w", encoding="utf-8", newline="").write(
            json.dumps(cat, ensure_ascii=False, separators=(",", ":")))

    print("mode:", "APPLY" if apply else "DRY-RUN")
    print("sheet files:", len(todo_files), "to-convert:", len(todo_files) - converted if not apply else converted)
    print("atlas keys:", added_keys, "| cards face-switched:", changed, "| re-enabled:", len(reenabled))
    print("face_variants:", variants_added, "| rules edits:", rules_changed)
    print("unmapped cards:", len(unmapped))
    for u in unmapped[:20]:
        print("   -", u[1], u[2])
    print("re-enabled list:", reenabled)
    # 例外確認
    print("variants detail:")
    for code, (mode, cell) in sorted(VARIANT_MAP.items()):
        print("   %-10s %-20s pack/9B_%d" % (code, mode, cell))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    run(apply=ap.parse_args().apply)
