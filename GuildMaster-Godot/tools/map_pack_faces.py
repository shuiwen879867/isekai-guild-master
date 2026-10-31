#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""map_pack_faces.py — Phase A：圖包拼圖 ↔ 卡號/卡名 自動對應 + 核查總圖。

流程：
  Pass 1  每格以「分段加權 SSD」（跳過文字帶）比對 native 紙底圖 + 完成卡
  Pass 2  卡背排除 → R1 同片重複碼 → R2 鄰序矛盾 → 序位填補（單族連續拼圖）
  Pass 2.5 跨片同碼衝突裁決（9B 變體拼圖不參與）
  Pass 3  總圖（格內印 卡號+分數）+ review_list.txt + map_result.json

已知背景：執行包內某些底圖其實是 Ⓑ/擴充替換面（如 847003=E-001 的 Ⓑ 版、
847000=E-007 的 Ⓑ 版），所以那些卡的原印面在底圖目標裡不存在，需靠序位規則定位。
"""

import argparse
import json
import os
import re
from collections import Counter

import numpy as np
from PIL import Image, ImageDraw, ImageFile
import PIL.ImageFont as IF
ImageFile.LOAD_TRUNCATED_IMAGES = False

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORT_ROOT = os.path.dirname(HERE)
SRC = os.path.join(os.path.dirname(EXPORT_ROOT), "GuildMaster-Godot-src")
PACK = os.path.join(os.path.dirname(EXPORT_ROOT), "圖包")
ART = os.path.join(EXPORT_ROOT, "art")
DEFAULT_OUT = os.path.join(os.environ.get("TEMP", "."), "opencode", "pack_review")

FILES = [
    ("1", "卡牌-1.png", 5, 4), ("2", "卡牌-2.png", 5, 4), ("3", "卡牌-3.png", 5, 4), ("4", "卡牌-4.png", 5, 4),
    ("5", "卡牌-5.png", 5, 4), ("6", "卡牌-6.png", 5, 4), ("7", "卡牌-7.png", 5, 4), ("8", "卡牌-8.png", 5, 4),
    ("9B", "卡牌-9(B面,擴).png", 5, 4), ("10", "卡牌-10.png", 5, 4), ("11", "卡牌-11.png", 5, 4),
    ("12", "卡牌-12.png", 5, 4), ("13", "卡牌-13.png", 5, 4), ("14", "卡牌-14.png", 5, 4),
    ("XG", "序章-1.png", 7, 3),
]
TW, TH = 168, 240
BANDS = [(0.00, 0.40, 0.45), (0.40, 0.62, 0.25), (0.84, 1.00, 0.30)]
VARIANT_TAG = "9B"  # 變體面拼圖（混族，順序不可靠，不參與序位/衝突規則）


def band_gray(im):
    arr = np.asarray(im.convert("RGB").resize((TW, TH), Image.BILINEAR)).astype(np.float32)
    return 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]


def band_score(g1, g2):
    total = 0.0
    for y0, y1, wgt in BANDS:
        total += wgt * float(np.abs(g1[int(y0 * TH):int(y1 * TH), :] - g2[int(y0 * TH):int(y1 * TH), :]).mean())
    return total


def find_font(size):
    for name in ("consola.ttf", "msyh.ttc", "arial.ttf"):
        p = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", name)
        if os.path.isfile(p):
            return IF.truetype(p, size)
    return IF.load_default()


def as_card(t):
    return {"id": t[0], "code": t[1], "name": t[2], "kind": t[3]} if t else None


def build_context(cat, lay):
    key2card = {}
    for cid, c in cat["cards"].items():
        key2card[c.get("image_path", "")] = (int(cid), c.get("printed_code", "") or "", c.get("name", ""), c.get("kind", ""))
    paper2cards = {}
    for base, spec in lay.items():
        pf = os.path.basename(spec.get("paper", "") or "")
        if pf:
            paper2cards.setdefault(pf, []).append(key2card.get(base, (None, "", "", "")))
    targets = {}
    pdir = os.path.join(ART, "images", "native_font_backgrounds")
    for base, spec in lay.items():
        pf = os.path.basename(spec.get("paper", "") or "")
        if not pf or pf in targets:
            continue
        path = os.path.join(pdir, pf)
        if not os.path.isfile(path):
            continue
        im = Image.open(path)
        w, h = im.size
        targets[("paper", pf)] = {"aspect": w / (h + 1e-9), "g": band_gray(im),
                                  "cards": [as_card(r) for r in paper2cards.get(pf, []) if r[0] is not None],
                                  "layout_key": base}
    ndir = os.path.join(ART, "images", "new_art")
    for f in os.listdir(ndir):
        if not f.endswith(".webp"):
            continue
        path = os.path.join(ndir, f)
        im = Image.open(path)
        w, h = im.size
        card = as_card(key2card.get("images/new_art/" + f))
        targets[("newart", f)] = {"aspect": w / (h + 1e-9), "g": band_gray(im),
                                  "cards": [card] if card else []}
    return key2card, paper2cards, targets


def code_num(code):
    m = re.match(r"([A-Z]+)-(\d+)", code or "")
    return (m.group(1), int(m.group(2))) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--scale", type=float, default=0.4)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    cat = json.load(open(os.path.join(SRC, "data", "catalog.json"), encoding="utf-8"))
    lay = json.load(open(os.path.join(SRC, "data", "card_layouts.json"), encoding="utf-8"))
    key2card, paper2cards, targets = build_context(cat, lay)
    tkeys = list(targets)
    tg = np.stack([targets[k]["g"] for k in tkeys])
    aspects = np.array([targets[k]["aspect"] for k in tkeys])
    review = []

    # --- Pass 1: 辨識 ---
    sheets = {}
    for tag, fname, cols, rows in FILES:
        path = os.path.join(PACK, fname)
        if not os.path.isfile(path):
            review.append("[missing] " + fname)
            continue
        im = Image.open(path).convert("RGB")
        W, H = im.size
        cw, ch = W / cols, H / rows
        cells = []
        for ri in range(rows):
            for ci in range(cols):
                cell_id = ri * cols + ci + 1
                x0, y0 = int(round(ci * cw)), int(round(ri * ch))
                x1, y1 = int(round((ci + 1) * cw)), int(round((ri + 1) * ch))
                cell = im.crop((x0, y0, x1, y1))
                rec = {"cell": cell_id, "box": [x0, y0, x1, y1]}
                arr8 = np.asarray(cell.resize((8, 8)))
                if arr8.mean() < 14:
                    rec["empty"] = True
                else:
                    g = band_gray(cell)
                    a = cell.width / (cell.height + 1e-9)
                    best = (1e9, None)
                    second = 1e9
                    for i, k in enumerate(tkeys):
                        if abs(aspects[i] - a) >= 0.08:
                            continue
                        s = band_score(g, tg[i])
                        if s < best[0]:
                            second = best[0]
                            best = (s, k)
                        elif s < second:
                            second = s
                    score, key = best
                    cards = targets[key]["cards"]
                    rec.update({"d": round(score, 1), "via": key[0], "hit": key[1],
                                "ambiguous": bool((second - score) < 3.5),
                                "multi": len(cards) > 1})
                    if cards:
                        rec["card"] = cards[0]
                    else:
                        lk = targets[key].get("layout_key", "")
                        rec["layout_key"] = lk
                        rec["layout_stem"] = lk.rsplit("/", 1)[-1].replace(".webp", "") if lk else key[1]
                cells.append(rec)
        sheets[fname] = {"tag": tag, "size": [W, H], "im": im, "cells": cells}

    # --- Pass 2: 卡背 / R1 / R2 / 序位填補 ---
    last_hits = Counter()
    for fname, sh in sheets.items():
        lastc = sh["cells"][-1]
        if not lastc.get("empty") and lastc.get("hit"):
            last_hits[lastc["hit"]] += 1
    back_targets = {k for k, n in last_hits.items() if n >= 3}

    def refs_excluding(sh, exclude):
        out = []
        for x in sh["cells"]:
            if x is exclude or not x.get("card") or x.get("back"):
                continue
            k = code_num(x["card"]["code"])
            if k:
                out.append((x["cell"], k))
        return out

    def fill_cand(sh, c, refs):
        before = [(n, k) for n, k in refs if n < c["cell"]]
        after = [(n, k) for n, k in refs if n > c["cell"]]
        if before and after:
            (ca, ka), (cb, kb) = before[-1], after[0]
            if ka[0] == kb[0]:
                if kb[1] - ka[1] == cb - ca:
                    return "%s-%03d" % (ka[0], ka[1] + (cb - c["cell"]))
                return None
            return "%s-%03d" % (ka[0], ka[1] + (c["cell"] - ca))
        if before:
            ca, ka = before[-1]
            return "%s-%03d" % (ka[0], ka[1] + (c["cell"] - ca))
        if after:
            cb, kb = after[0]
            return "%s-%03d" % (kb[0], kb[1] - (cb - c["cell"]))
        return None

    for fname, sh in sheets.items():
        # (a) 卡背排除
        for c in sh["cells"]:
            if not c.get("empty") and c.get("hit") in back_targets:
                c["back"] = True
                c.pop("card", None)

        # (R1) 同片重複碼
        code_cells = {}
        for c in sh["cells"]:
            if c.get("card") and code_num(c["card"]["code"]):
                code_cells.setdefault(c["card"]["code"], []).append(c)
        for code, cl in code_cells.items():
            if len(cl) < 2:
                continue
            kinfo = code_num(code)
            keep = None
            for c in cl:
                refs = refs_excluding(sh, c)
                ok = False
                for n, k in refs:
                    if k[0] != kinfo[0]:
                        continue
                    step = abs(c["cell"] - n)
                    if step <= 2 and k[1] + (c["cell"] - n) == kinfo[1]:
                        ok = True
                        break
                if ok:
                    keep = c
                    break
            for c in cl:
                if keep is not None and c is keep:
                    continue
                cand = fill_cand(sh, c, refs_excluding(sh, c))
                if cand and cand != code:
                    hits = [v for v in key2card.values() if v[1] == cand]
                    if hits:
                        c["sequence_overrode"] = code
                        c["card"] = as_card(hits[0])
                        c["filled_by_sequence"] = True
                        review.append("%s c%d → R1 同片重複碼 %s→%s" % (fname, c["cell"], code, cand))
                        continue
                review.append("%s c%d → R1 未解（重複 %s）" % (fname, c["cell"], code))

        # (R2) 鄰序矛盾 + (b) 保留/填補
        for c in sh["cells"]:
            if c.get("empty") or c.get("back"):
                continue
            if sh["tag"] == VARIANT_TAG:
                continue
            if c.get("card"):
                li, ri2 = c["cell"] - 2, c["cell"]
                L = sh["cells"][li] if 0 <= li < len(sh["cells"]) else None
                R = sh["cells"][ri2] if 0 <= ri2 < len(sh["cells"]) else None
                if L and R and L.get("card") and R.get("card"):
                    kl, kr = code_num(L["card"]["code"]), code_num(R["card"]["code"])
                    if kl and kr and kl[0] == kr[0] and kr[1] - kl[1] == 2:
                        pred = "%s-%03d" % (kl[0], kl[1] + 1)
                        if c["card"]["code"] != pred:
                            hits = [v for v in key2card.values() if v[1] == pred]
                            if hits:
                                review.append("%s c%d → R2 鄰序矛盾 %s→%s" % (fname, c["cell"], c["card"]["code"], pred))
                                c["sequence_overrode"] = c["card"]["code"]
                                c["card"] = as_card(hits[0])
                                c["filled_by_sequence"] = True
                if c.get("card") and c["d"] <= 22 and not c.get("ambiguous"):
                    continue
            cand = fill_cand(sh, c, refs_excluding(sh, c))
            if cand:
                hits = [v for v in key2card.values() if v[1] == cand]
                if hits:
                    if c.get("card") and c["card"]["code"] != cand:
                        c["sequence_overrode"] = c["card"]["code"]
                    c["card"] = as_card(hits[0])
                    c["filled_by_sequence"] = True
                    c.pop("layout_stem", None)

    # --- Pass 2.5: 跨片同碼衝突裁決（9B 變體片不參與）---
    by_code = {}
    for fname, sh in sheets.items():
        if sh["tag"] == VARIANT_TAG:
            continue
        for c in sh["cells"]:
            if c.get("card"):
                by_code.setdefault(c["card"]["code"], []).append((fname, c))
    for code, lst in by_code.items():
        if len(lst) <= 1:
            continue
        direct = [x for x in lst if not x[1].get("filled_by_sequence")]
        keep = direct if direct else lst[:1]
        keep_ids = set(id(x[1]) for x in keep)
        for f, c in lst:
            if id(c) not in keep_ids:
                review.append("%s c%d → 跨片衝突退回 %s（保留於 %s）" % (
                    f, c["cell"], code, "、".join(x[0] for x in keep)))
                c["card"] = None
                c["conflict_dropped"] = code

    # --- Pass 3: 總圖 + 報告 ---
    result = {}
    for fname, sh in sheets.items():
        tag = sh["tag"]
        W, H = sh["size"]
        cols, rows = 5, 4
        cw, ch = W / cols, H / rows
        labels = {}
        for c in sh["cells"]:
            ri, ci = divmod(c["cell"] - 1, cols)
            if c.get("empty"):
                lab = "c%d [empty]" % c["cell"]
            elif c.get("back"):
                lab = "c%d [back]" % c["cell"]
            elif c.get("card"):
                lab = "c%d %s #%s%s%s" % (c["cell"], c["card"]["code"], c["card"]["id"],
                                          "+" if c.get("multi") else "",
                                          "~" if c.get("filled_by_sequence") else "")
            else:
                lab = "c%d [%s] %d" % (c["cell"], c.get("layout_stem", "?"), int(c.get("d", 0)))
            labels[(ri, ci)] = lab
        scale = args.scale
        tw, th = int(W * scale / cols), int(H * scale / rows)
        M = Image.new("RGB", (tw * cols, th * rows), "white")
        draw = ImageDraw.Draw(M)
        font = find_font(max(13, int(tw * 0.045)))
        for ri in range(rows):
            for ci in range(cols):
                x0, y0 = int(round(ci * cw)), int(round(ri * ch))
                cell = sh["im"].crop((x0, y0, int(round((ci + 1) * cw)), int(round((ri + 1) * ch)))).resize((tw, th))
                M.paste(cell, (ci * tw, ri * th))
                lab = labels[(ri, ci)]
                wpx = draw.textlength(lab, font=font)
                draw.rectangle([ci * tw, ri * th, ci * tw + wpx + 8, ri * th + 20], fill=(255, 255, 200))
                draw.text((ci * tw + 4, ri * th + 2), lab, font=font, fill=(120, 0, 0))
                draw.rectangle([ci * tw, ri * th, (ci + 1) * tw - 1, (ri + 1) * th - 1], outline=(140, 140, 140))
        M.save(os.path.join(args.out, "%s_montage.png" % tag))
        result[fname] = {"tag": tag, "size": [W, H], "cells": sh["cells"]}

        if tag == VARIANT_TAG:
            corner_w, corner_h = int(cw * 0.34), int(ch * 0.42)
            per_row = 7
            tw2, th2 = int(corner_w * 0.62), int(corner_h * 0.62)
            rows_n = (len(sh["cells"]) + per_row - 1) // per_row
            C = Image.new("RGB", (per_row * (tw2 + 8), rows_n * (th2 + 24)), "white")
            d2c = ImageDraw.Draw(C)
            fc = find_font(15)
            for i, c in enumerate(sh["cells"]):
                x0, y0, x1, y1 = c["box"]
                crop = sh["im"].crop((x1 - corner_w, y0 + int(ch * 0.02), x1, y0 + int(ch * 0.02) + corner_h))
                px, py = (i % per_row) * (tw2 + 8), (i // per_row) * (th2 + 24)
                C.paste(crop.resize((tw2, th2)), (px, py + 22))
                d2c.text((px + 2, py + 2), "c%d %s" % (c["cell"], (c.get("card") or {}).get("code") or "?"), font=fc, fill=(160, 0, 0))
            C.save(os.path.join(args.out, "9B_corners.png"))

    open(os.path.join(args.out, "map_result.json"), "w", encoding="utf-8").write(
        json.dumps(result, ensure_ascii=False, indent=1))
    open(os.path.join(args.out, "review_list.txt"), "w", encoding="utf-8").write("\n".join(review))

    tot = sum(len(r["cells"]) for r in result.values())
    empt = sum(1 for r in result.values() for c in r["cells"] if c.get("empty"))
    backs = sum(1 for r in result.values() for c in r["cells"] if c.get("back"))
    filled = sum(1 for r in result.values() for c in r["cells"] if c.get("filled_by_sequence"))
    identified = tot - empt - backs - sum(1 for r in result.values() for c in r["cells"]
                                          if not c.get("empty") and not c.get("back") and not c.get("card"))
    print("montages: %s" % args.out)
    print("cells: %d  empty: %d  back: %d  with-card: %d (direct %d / seq %d)" % (
        tot, empt, backs, identified + filled, identified, filled))
    for fname, r in result.items():
        line = " | ".join((("%s%s" % (c["card"]["code"] or c["card"]["id"], "~" if c.get("filled_by_sequence") else ""))
                           if (not c.get("empty") and not c.get("back") and c.get("card"))
                           else ("back" if c.get("back") else ("emp" if c.get("empty") else "[?]"))) for c in r["cells"])
        print("%-3s %s" % (r["tag"], line))


if __name__ == "__main__":
    main()
