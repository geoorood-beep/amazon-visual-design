#!/usr/bin/env python3
"""Uta Style 调色自检：python3 grade_check.py img1.jpg [img2.jpg ...]
输出与 UTA_STYLE_STANDARD.md 第 9 节同口径；暗场模块加 --dark的数值（0–1 标度），并标出越界项。
只用于生活场景/暗场模块；纯色底与白底图不适用。"""
import sys
import numpy as np
from PIL import Image
T = {  # 生活场景（暖）目标区间，来自 oneisall 20 款 577 张非白底图的中位数 ± 容差
    'L_mean': (0.45, 0.60), 'L_std': (0.20, 0.28), 'p5': (0.06, 0.14),
    'p95': (0.85, 0.95), 'sat': (0.26, 0.38), 'warm_RminusB': (0.10, 0.20)}
D = {  # 暗场科技/夜景（第 9.1 节 B 模式）
    'L_mean': (0.27, 0.33), 'L_std': (0.16, 0.20), 'p5': (0.04, 0.09),
    'p95': (0.55, 0.70), 'sat': (0.30, 0.55), 'warm_RminusB': (0.10, 0.18)}
args = sys.argv[1:]
if args and args[0] == '--dark':
    T = D; args = args[1:]
for f in args:
    a = np.asarray(Image.open(f).convert('RGB').resize((400, 400))).astype(float) / 255
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    L = .2126 * r + .7152 * g + .0722 * b
    mx, mn = a.max(2), a.min(2)
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    v = {'L_mean': L.mean(), 'L_std': L.std(), 'p5': np.percentile(L, 5),
         'p95': np.percentile(L, 95), 'sat': s.mean(), 'warm_RminusB': (r - b).mean()}
    out = [f'{k}={x:.3f}' + ('' if T[k][0] <= x <= T[k][1] else f'(!{T[k][0]}–{T[k][1]})') for k, x in v.items()]
    print(f, ' '.join(out))
