# -*- coding: utf-8 -*-
"""make_tile_backs.py — 從實體掃描製作缺漏的迷宮板塊背面素材。

rules/guild_asset_manifest.json 需要：
  083.webp = 變動板塊背面（藍底雙星）：以標準幾何合成——深棕木框＋藍磚紋內面（取自變動照片）＋兩顆白星
  087.webp = 2星魔王背面（掃描已在標準幾何，直接轉檔）
  088.webp = 4星魔王背面（同上）
標準幾何：750×750 畫布，六角形寬 750（左右頂點貼邊）、高 661（上下平邊在 y=44/705）。
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw

PACK = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', '圖包'))
OUT = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'art', 'images', 'tts'))
CANVAS, HEX_H, HEX_TOP, CENTER = 750, 661, 44, 375


def pick(*ends):
    names = [f for f in os.listdir(PACK) if f.lower().endswith('.jpg')]
    for f in names:
        if f.endswith(ends):
            return os.path.join(PACK, f)
    raise FileNotFoundError(ends)


def hexagon(radius_y, radius_x, center):
    """平顶朝上的六角形（上下为平边）：顶点 = 中心 + (±radius_x, 0) 与四角。"""
    pts = []
    for i in range(6):
        angle = math.radians(i * 60)
        x = math.cos(angle); y = math.sin(angle)
        pts.append((center[0] + x * radius_x, center[1] + y * radius_y))
    return pts


def hexagon_points(r_y, r_x, c):
    return [(c[0] + dx * r_x, c[1] + dy * r_y) for dx, dy in
            ((1, 0), (0.5, 0.866), (-0.5, 0.866), (-1, 0), (-0.5, -0.866), (0.5, -0.866))]


def interior_inset_of(scan_path, is_red):
    im = Image.open(scan_path).convert('RGB')
    a = np.asarray(im).astype(int)
    if is_red:
        inner = (a[:, :, 0] > a[:, :, 1] + 40) & (a[:, :, 0] > a[:, :, 2] + 40)
    else:
        inner = (abs(a[:, :, 0] - a[:, :, 1]) < 28) & (abs(a[:, :, 1] - a[:, :, 2]) < 28) & (a.sum(axis=2) < 560)
    ys, xs = np.where(inner)
    counts = np.zeros(im.width);
    for x in range(im.width):
        counts[x] = (xs == x).sum()
    valid = np.where(counts >= 30)[0]
    left, right = int(valid.min()), int(valid.max())
    print(os.path.basename(scan_path), '内面左右 x %d..%d（宽 %d）→ 单边内缩 %d' % (left, right, right - left, min(left, CANVAS - 1 - right)))


def build_variable_back(dst, brick_box=(110, 130, 640, 620)):
    photo = Image.open(pick('\u8b8a\u52d5-\u80cc\u9762.jpg')).convert('RGB')
    # 取照片内面的平均蓝色作为底色（向量式干净内面，避免照片白底/双星残影）。
    a = np.asarray(photo).astype(int)
    blue = (a[:, :, 2] > a[:, :, 0] + 40) & (a[:, :, 2] > a[:, :, 1] + 40) & (a[:, :, 2] > 100)
    r = int(a[:, :, 0][blue].mean()); g = int(a[:, :, 1][blue].mean()); b = int(a[:, :, 2][blue].mean())
    canvas = Image.new('RGBA', (CANVAS, CANVAS), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    outer = hexagon_points(HEX_H / 2.0, CANVAS / 2.0, (CENTER, CENTER))
    d.polygon(outer, fill=(74, 50, 31, 255))                      # 深棕木框
    inner_r_x, inner_r_y = CANVAS / 2.0 - 57, HEX_H / 2.0 - 55
    d.polygon(hexagon_points(inner_r_y, inner_r_x, (CENTER, CENTER)), fill=(r, g, b, 255))
    # 两颗白色星星（左下／右上，对称于中心）。
    for dx, dy in ((-72, 118), (72, -118)):
        pts = []
        for i in range(10):
            ang = math.radians(i * 36 - 90)
            reach = 100 if i % 2 == 0 else 42
            pts.append((CENTER + dx + math.cos(ang) * reach, CENTER + dy + math.sin(ang) * reach))
        d.polygon(pts, fill=(255, 255, 255, 255))
    canvas.save(dst, 'WEBP', quality=90, method=4)
    print(dst, '%.2fMB' % (os.path.getsize(dst) / 1048576))


if __name__ == '__main__':
    interior_inset_of(pick('2\u661f\u9b54\u738b\u80cc\u9762.jpg'), True)
    interior_inset_of(pick('\u666e\u901a\u80cc\u9762.jpg'), False)
    build_variable_back(os.path.join(OUT, '083.webp'))
    for name, ends in (('087.webp', ('2\u661f\u9b54\u738b\u80cc\u9762.jpg',)), ('088.webp', ('4\u661f\u9b54\u738b\u80cc\u9762.jpg',))):
        im = Image.open(pick(*ends)).convert('RGB')
        im.save(os.path.join(OUT, name), 'WEBP', quality=88, method=4)
        print(name, im.size, '%.2fMB' % (os.path.getsize(os.path.join(OUT, name)) / 1048576))
