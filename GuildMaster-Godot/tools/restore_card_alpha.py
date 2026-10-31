#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""restore_card_alpha.py — 修復完成卡在 Godot 中四角出現黑色／藍色／白墊的問題。

根因（已驗證）：
  * art/images/new_art/*.webp 是「圓角卡壓在畫板白墊上」烘焙的 RGB webp（無 alpha）；
    部分卡的下角還露出卡自身的黑框帶 / rank 藍色 footer 帶。
  * 遊戲端 GuildArtStore.texture() 以執行檔相對路徑 Image.load_from_file() 直讀磁碟，
    完全繞過 Godot 匯入參數（fix_alpha_border 不生效）。
  * card_art.gd 直接 draw_texture_rect 畫出整張檔案，圓角外的白墊／黑帶／藍帶因而露出。

做法：
  1. 對每個角量測白墊剖面：先數直邊留白列數（margin），深部列的 run = 直邊側留白，
     再以弧線方程式 (r-run')^2 + (r-yp)^2 = r^2 擬合半徑（中位數抗噪）。
  2. 依內容矩形 + 四角半徑生成羽化圓角 alpha 遮罩；弧外／留白 alpha=0。
  3. alpha=0 的像素 RGB 以相鄰不透明像素擴張（bake fix_alpha_border 等效果），
     避免執行期雙線性縮放時黑 RGB 暈到卡面。
  4. 以 webp 帶 alpha 存回原路徑（q90 method=6），尺寸與路徑不變，不需重建 pck。

用法：
  python tools/restore_card_alpha.py            # 乾跑：只輸出偵測報告，不寫檔
  python tools/restore_card_alpha.py --apply    # 實際處理（先備份原檔到 --backup）
  python tools/restore_card_alpha.py --verify   # 依 --backup 的原始檔還原幾何，對現況做像素斷言
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
ART_DIR = os.path.join(ROOT, "art", "images", "new_art")

SKIP_BORDER_PX = 2      # 圖邊常有 1~2px 深色框線，量測時先跳過
PAD_LUM = 232.0         # 白墊亮度門檻（實測墊為白／米色）
MAX_PROBE = 170         # 角剖面最大探測深度（px）
MARGIN_RUN = 300        # 白程長度 >= 此值視為直邊留白
MAX_RADIUS = 150.0      # 半徑合理上限
MAX_MARGIN = 60         # 直邊留白合理上限（超過視為異常）
FEATHER = 1.5           # 弧邊羽化寬度（px）
REACH = 12              # RGB 向外擴張的最大深度（px）
QUALITY = 90            # webp 存檔品質


def detect(arr):
    """回傳 {'w':, 'h':, 'corners':{name:{'margin','radius','side_margin'}}}"""
    h, w = arr.shape[:2]
    lum = arr[..., 0] * 0.299 + arr[..., 1] * 0.587 + arr[..., 2] * 0.114
    is_pad = lum >= PAD_LUM

    result = {"w": w, "h": h, "corners": {}}
    for name in ("TL", "TR", "BL", "BR"):
        dy = 1 if name in ("TL", "TR") else -1
        dx = 1 if name in ("TL", "BL") else -1
        rows = []
        probe = min(MAX_PROBE, h - 1)
        for i in range(probe + 1):
            y = 0 + i if dy > 0 else h - 1 - i
            startx = 0 if dx > 0 else w - 1
            def edge_ok(xx, dx=dx, w=w):
                return (xx < w - 1) if dx > 0 else (xx > 0)

            def white_from(xx):
                n = 0
                while edge_ok(xx) and n < MARGIN_RUN and is_pad[y, xx]:
                    n += 1
                    xx += dx
                return n

            # 型態判定：邊緣即白 → 純白程；
            # 邊緣暗但 ≤6px 後接白 → 暗框線覆蓋白墊（run 計入框線厚度）；
            # 邊緣暗且 >6px 無白 → 此列為內容（深部），run=0
            if is_pad[y, startx]:
                run = white_from(startx)
            else:
                xx = startx
                L = 0
                while edge_ok(xx) and not is_pad[y, xx] and L < 6:
                    L += 1
                    xx += dx
                if L < 6 and edge_ok(xx) and is_pad[y, xx]:
                    run = L + white_from(xx)
                else:
                    run = 0
            rows.append((i, run))

        # 直邊留白：開頭整段都是白程
        margin = 0
        for i, run in rows:
            if run >= MARGIN_RUN:
                margin += 1
            else:
                break
        if margin >= probe:
            result["corners"][name] = {"margin": margin, "radius": None,
                                       "side_margin": float(MARGIN_RUN)}
            continue

        # 兩階段弧擬合：先取前段列估起始半徑，再用該半徑限制有效列範圍
        def estimate(yp_limit):
            est = []
            for i, run in rows[margin:]:
                yp = float(i - margin)
                if yp > yp_limit:
                    break
                if run < 2.0:
                    continue
                x0 = float(run)
                if yp == 0.0:
                    est.append(x0)
                else:
                    r_h = x0 + yp + math.sqrt(2.0 * x0 * yp)
                    if 0 < r_h < MAX_RADIUS:
                        est.append(r_h)
            if not est:
                return 0.0
            return float(sorted(est)[len(est) // 2])

        radius = estimate(12.0)
        if radius > 0:
            radius = estimate(min(radius + 6.0, MAX_RADIUS))

        # 深部側邊留白：弧結束之後（yp > radius）的列白程
        side_vals = [float(run) for i, run in rows[margin:]
                     if (i - margin) > radius and run > 0]
        side = float(sorted(side_vals)[len(side_vals) // 2]) if side_vals else 0.0

        result["corners"][name] = {
            "margin": margin,
            "radius": radius,
            "side_margin": side,
        }

    # 四角半徑共識：卡片四角半徑理應相同；用同卡中位數夾限各角，
    # 防止個別角因白綬帶等深色/亮色內容溢出而被擬合成過大的假弧，
    # 同時救援因邊框線而擬合失敗（=0）的角。
    vals = [result["corners"][k]["radius"] for k in result["corners"]]
    if all(v is not None for v in vals) and len(set(map(round, vals))) > 0:
        med = float(sorted(vals)[len(vals) // 2])
        for k in result["corners"]:
            v = result["corners"][k]["radius"]
            if v < 2.0 and med >= 8.0:
                v = med
            v = min(max(v, med - 10.0), med + 10.0)
            result["corners"][k]["radius"] = v
    return result


def corner_mask(w, h, rect, corners, feather=FEATHER):
    """rect=(x0,y0,x1,y1) 含端點; corners 為 detect() 的 corners dict。回傳 float alpha(0..1)。"""
    x0, y0, x1, y1 = rect
    xs = np.arange(w, dtype=np.float32) + 0.5
    ys = np.arange(h, dtype=np.float32) + 0.5
    X, Y = np.meshgrid(xs, ys)

    core = ((X >= x0 + feather) & (X <= x1 + 1 - feather)
            & (Y >= y0 + feather) & (Y <= y1 + 1 - feather))
    edge = ((X >= x0) & (X <= x1 + 1) & (Y >= y0) & (Y <= y1 + 1))
    alpha = np.maximum(core.astype(np.float32), edge.astype(np.float32) * 0.82)

    for name in ("TL", "TR", "BL", "BR"):
        r = corners.get(name, {}).get("radius") or 0.0
        if r <= 2.0:
            continue
        r = min(r, (x1 - x0) * 0.49, (y1 - y0) * 0.49)
        ax = x0 + r if name in ("TL", "BL") else x1 + 1 - r
        ay = y0 + r if name in ("TL", "TR") else y1 + 1 - r
        d = np.hypot(X - ax, Y - ay)
        axzone = (X < ax) if name in ("TL", "BL") else (X > ax)
        ayzone = (Y < ay) if name in ("TL", "TR") else (Y > ay)
        arc_a = np.clip(((r + feather / 2.0) - d) / feather, 0.0, 1.0)
        alpha = np.where(axzone & ayzone, np.minimum(alpha, arc_a), alpha)
    return alpha


def spread_rgb(rgb, alpha01, reach=REACH):
    """alpha=0 的像素 RGB 以鄰近不透明像素擴張（迭代 reach 層）。"""
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


def process_file(path, backup_dir=None, quality=QUALITY, dry=False):
    rgba = np.asarray(Image.open(path).convert("RGBA")).astype(np.float32)
    h, w = rgba.shape[:2]
    info = detect(rgba)
    cs = info["corners"]
    if any(cs[k]["radius"] is None for k in cs):
        return {"file": os.path.basename(path), "status": "skip", "reason": "blank-margin"}
    if all((cs[k]["radius"] or 0.0) == 0.0 and cs[k]["margin"] == 0 and cs[k]["side_margin"] == 0 for k in cs):
        return {"file": os.path.basename(path), "status": "keep", "reason": "no-pad"}
    for k in cs:
        if cs[k]["radius"] is not None and cs[k]["radius"] > MAX_RADIUS:
            return {"file": os.path.basename(path), "status": "skip", "reason": "radius-too-big:%s" % k}
        if cs[k]["margin"] > MAX_MARGIN:
            return {"file": os.path.basename(path), "status": "skip", "reason": "margin-too-big:%s" % k}

    x0 = int(round(cs["TL"]["side_margin"]))
    y0 = int(cs["TL"]["margin"])
    x1 = w - 1 - int(round(cs["TR"]["side_margin"]))
    y1 = h - 1 - int(cs["BL"]["margin"])
    radii = [(cs[k]["radius"] or 0.0) for k in ("TL", "TR", "BL", "BR")]

    alpha01 = corner_mask(w, h, (x0, y0, x1, y1), cs)
    alpha08 = (alpha01 * 255.0).astype(np.uint8)
    rgb = spread_rgb(rgba[..., :3], alpha01)
    out = Image.fromarray(np.dstack([rgb.clip(0, 255).astype(np.uint8), alpha08]), "RGBA")

    old_size = os.path.getsize(path)
    if dry:
        return {"file": os.path.basename(path), "status": "would",
                "rect": [x0, y0, x1, y1], "radii": [round(r, 1) for r in radii],
                "old_size": old_size}
    if backup_dir:
        os.makedirs(backup_dir, exist_ok=True)
        dst = os.path.join(backup_dir, os.path.basename(path))
        if not os.path.exists(dst):
            shutil.copy2(path, dst)
    tmp = path + ".tmp.webp"
    out.save(tmp, "WEBP", quality=quality, method=6)
    os.replace(tmp, path)
    return {"file": os.path.basename(path), "status": "ok",
            "rect": [x0, y0, x1, y1],
            "radii": [round(r, 1) for r in radii],
            "old_size": old_size, "new_size": os.path.getsize(path)}


def verify_file(path, backup_path):
    old = np.asarray(Image.open(backup_path).convert("RGB")).astype(np.float32)
    info = detect(old)
    cs = info["corners"]
    if any(cs[k]["radius"] is None for k in cs):
        return {"file": os.path.basename(path), "status": "not-processed"}
    if all((cs[k]["radius"] or 0.0) == 0.0 and cs[k]["margin"] == 0 and cs[k]["side_margin"] == 0 for k in cs):
        return {"file": os.path.basename(path), "status": "untouched"}

    now = np.asarray(Image.open(path).convert("RGBA"))
    h, w = now.shape[:2]
    a = now[..., 3].astype(int)
    lum = now[..., 0] * 0.299 + now[..., 1] * 0.587 + now[..., 2] * 0.114

    problems = []
    for name, (xx, yy) in (("TL", (0, 0)), ("TR", (w - 1, 0)), ("BL", (0, h - 1)), ("BR", (w - 1, h - 1))):
        r = cs[name]["radius"] or 0.0
        if r > 2 and a[yy, xx] != 0:
            problems.append("corner-not-transparent:%s alpha=%d" % (name, a[yy, xx]))

    x0 = int(round(cs["TL"]["side_margin"]))
    y0 = cs["TL"]["margin"]
    x1 = w - 1 - int(round(cs["TR"]["side_margin"]))
    y1 = h - 1 - cs["BL"]["margin"]

    # 弧外側（對角線上、理想弧之外的 2~5px 環）不應有殘留
    dcx = {"TL": 1, "TR": -1, "BL": 1, "BR": -1}
    dcy = {"TL": 1, "TR": 1, "BL": -1, "BR": -1}
    for name in ("TL", "TR", "BL", "BR"):
        r = cs[name]["radius"] or 0.0
        if r <= 6:
            continue
        k = int(r * (1.0 - 1.0 / math.sqrt(2.0)))
        for off in range(2, 6):
            xx = (0 if dcx[name] > 0 else w - 1) + dcx[name] * max(1, k - off)
            yy = (0 if dcy[name] > 0 else h - 1) + dcy[name] * max(1, k - off)
            if 0 <= xx < w and 0 <= yy < h and a[yy, xx] > 0 and lum[yy, xx] > 195:
                problems.append("arc-sliver:%s @(%d,%d) a=%d lum=%.0f" % (name, xx, yy, a[yy, xx], lum[yy, xx]))
                break

    # 直邊留白應完全消失（僅在 margin/side_margin 存在時檢查）
    ring = np.zeros((h, w), bool)
    if y0 > 0:
        ring[max(0, y0 - 2):y0, :] = True
    if y1 < h - 1:
        ring[y1 + 1:min(h, y1 + 3), :] = True
    if x0 > 1:
        ring[:, max(0, x0 - 2):x0] = True
    if x1 < w - 1:
        ring[:, x1 + 1:min(w, x1 + 3)] = True
    if ring.any():
        bad = int((ring & (a > 0) & (lum > 200)).sum())
        if bad > 0:
            problems.append("bright-residue=%d" % bad)
    return {"file": os.path.basename(path),
            "status": "ok" if not problems else "fail",
            "problems": problems}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--backup", default=os.path.join(os.environ.get("TEMP", "."), "opencode", "new_art_backup"))
    args = ap.parse_args()

    files = [f for f in sorted(glob.glob(os.path.join(ART_DIR, "*.webp"))) if not f.endswith(".import")]
    results = []

    if args.apply:
        for f in files:
            results.append(process_file(f, backup_dir=args.backup))
    else:
        for f in files:
            results.append(process_file(f, dry=True))

    if args.verify:
        results = []
        for f in files:
            b = os.path.join(args.backup, os.path.basename(f))
            if not os.path.exists(b):
                continue
            results.append(verify_file(f, b))
        fails = [r for r in results if r.get("status") == "fail"]
        print(json.dumps(fails if fails else [{"result": "all-ok", "count": len(results)}], ensure_ascii=False))
        print("verify: %d files, %d fail" % (len(results), len(fails)))
        return

    for r in results:
        print(json.dumps(r, ensure_ascii=False))
    ok = sum(1 for r in results if r.get("status") == "ok")
    proc = sum(1 for r in results if r.get("status") in ("ok", "would"))
    print("summary: %d files, %d will-process/processed, ok=%d" % (len(results), proc, ok))


if __name__ == "__main__":
    main()
