#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bake_transparent_rgb.py — 給「帶透明的符號/娃娃/圖示」素材把透明區 RGB bake 成鄰近不透明色。

背景：遊戲端以 Image.load_from_file() 直讀磁碟（繞過 fix_alpha_border），
透明像素的 RGB 是黑的話，雙線性縮放會把黑暈到邊緣（文字符號、娃娃、圖示周圍的暗邊）。
本工具僅改「alpha=0 像素的 RGB」，不動任何 alpha 值與不透明像素。

對象：
  * art/images/card_components/*-glyphs.webp（文字符號層，透明 RGB 多為黑）
  * art/images/ui/*.png（娃娃 red/blue/green/yellow/white、dragon、icon 等 RGBA png）

存檔策略：glyphs 以 webp lossless 重存（避免文字二次失真）；ui png 同名回存。

用法：
  python tools/bake_transparent_rgb.py            # 乾跑：輸出統計
  python tools/bake_transparent_rgb.py --apply    # 實處理（先備份到 --backup）
  python tools/bake_transparent_rgb.py --verify   # 斷言：alpha 與不透明像素逐位元不變
"""

import argparse
import glob
import json
import math
import os
import shutil
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TARGETS = [
    (os.path.join(ROOT, "art", "images", "card_components"), "*-glyphs.webp", "lossless-keep"),
    (os.path.join(ROOT, "art", "images", "ui"), "*.png", "png-keep"),
    (os.path.join(ROOT, "art", "images", "ui"), "*.webp", "lossless-keep"),
]
REACH = 12  # RGB 擴張層數


def spread_rgb(rgb, alpha01, reach=REACH):
    opaque = alpha01 > 0.0
    out = rgb.astype(np.float32).copy()
    h, w = opaque.shape
    for _ in range(reach):
        fringe = (~opaque)
        if not fringe.any():
            break
        acc = np.zeros_like(out)
        cnt = np.zeros((h, w), dtype=np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            valid = np.zeros((h, w), dtype=bool)
            val = np.zeros_like(out)
            if dy == 1:
                valid[:-1, :] = opaque[1:, :]
                val[:-1, :] = out[1:, :]
            elif dy == -1:
                valid[1:, :] = opaque[:-1, :]
                val[1:, :] = out[:-1, :]
            elif dx == 1:
                valid[:, :-1] = opaque[:, 1:]
                val[:, :-1] = out[:, 1:]
            elif dx == -1:
                valid[:, 1:] = opaque[:, :-1]
                val[:, 1:] = out[:, :-1]
            contrib = valid & fringe
            acc += val * contrib[..., None]
            cnt += contrib.astype(np.float32)
        fill = fringe & (cnt > 0)
        if not fill.any():
            break
        out[fill] = acc[fill] / cnt[fill][:, None]
        opaque = opaque | fill
    return out


def process(path, backup_dir=None, dry=True):
    rgba = np.asarray(Image.open(path).convert("RGBA"))
    h, w = rgba.shape[:2]
    a = rgba[..., 3]
    opaque = a > 0
    if opaque.all():
        return {"file": os.path.basename(path), "status": "keep", "reason": "fully-opaque"}
    # 目前透明 RGB 的黑傾向統計
    trans = ~opaque
    dark = float((rgba[..., :3][trans].mean(axis=-1) < 32).mean()) if trans.any() else 0.0
    out_rgb = spread_rgb(rgba[..., :3], (a * 255 > 0).astype(np.float32))
    new = np.dstack([out_rgb.clip(0, 255).astype(np.uint8), a])
    if dry:
        return {"file": os.path.basename(path), "status": "would",
                "transparent_px": int(trans.sum()), "dark_rgb_ratio": round(dark, 3)}
    if backup_dir:
        os.makedirs(backup_dir, exist_ok=True)
        dst = os.path.join(backup_dir, os.path.basename(path))
        if not os.path.exists(dst):
            shutil.copy2(path, dst)
    old_size = os.path.getsize(path)
    tmp = path + ".tmp"
    img = Image.fromarray(new, "RGBA")
    if path.lower().endswith(".png"):
        img.save(tmp, "PNG")
    else:
        img.save(tmp, "WEBP", lossless=True)
    os.replace(tmp, path)
    return {"file": os.path.basename(path), "status": "ok",
            "transparent_px": int(trans.sum()),
            "dark_rgb_ratio_before": round(dark, 3),
            "old_size": old_size, "new_size": os.path.getsize(path)}


def verify(path, backup_path):
    new = np.asarray(Image.open(path).convert("RGBA"))
    old = np.asarray(Image.open(backup_path).convert("RGBA"))
    same_shape = new.shape == old.shape
    a_same = same_shape and (new[..., 3] == old[..., 3]).all()
    both_opaque = (old[..., 3] > 0)
    rgb_same_opaque = same_shape and (new[..., :3][both_opaque] == old[..., :3][both_opaque]).all()
    tmask = old[..., 3] == 0
    improved = same_shape and float((np.abs(new[..., :3].astype(int) - old[..., :3].astype(int))[tmask]).sum() > 0)
    return {"file": os.path.basename(path),
            "ok": bool(same_shape and a_same and rgb_same_opaque),
            "alpha_identical": bool(a_same),
            "opaque_rgb_identical": bool(rgb_same_opaque),
            "transparent_rgb_changed": bool(improved)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--backup", default=os.path.join(os.environ.get("TEMP", "."), "opencode", "glyph_ui_backup"))
    args = ap.parse_args()

    files = []
    for root, pattern, _mode in TARGETS:
        files += [f for f in sorted(glob.glob(os.path.join(root, pattern))) if not f.endswith(".import")]

    results = []
    if args.verify:
        n_ok = 0
        for f in files:
            b = os.path.join(args.backup, os.path.basename(f))
            if not os.path.exists(b):
                continue
            rep = verify(f, b)
            n_ok += int(rep["ok"])
            results.append(rep)
        bad = [r for r in results if not r["ok"]]
        print(json.dumps(bad if bad else [{"result": "all-ok", "count": n_ok}], ensure_ascii=False))
        print("verify: %d files, %d fail" % (len(results), len(bad)))
        return

    for f in files:
        results.append(process(f, backup_dir=args.backup if args.apply else None, dry=not args.apply))

    for r in results:
        print(json.dumps(r, ensure_ascii=False))
    ok = sum(1 for r in results if r.get("status") == "ok")
    print("summary: %d files, %d ok" % (len(results), ok))


if __name__ == "__main__":
    main()
