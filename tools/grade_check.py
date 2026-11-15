#!/usr/bin/env python3
"""Uta Style 调色与尺寸自检。

用法：
  python3 tools/grade_check.py [--dark|--outdoor|--contrast] [--json]
      [--slot G1|S|AP-PC|AP-M] img [img ...]

默认是 UTA §9.1 A 档的六项指标，但暗部 p5 按 2026-11-15 确认的 D3
改为 p5 ≤ 0.12，不再使用 0.12–0.24 这一历史下限。
--contrast 改按 §6F：p5 ≤ 0.12、p95−p5 ≥ 0.80、亮度标准差 ≥ 0.25、
L<0.2 的像素占 10%–20%，平均亮度仍是 0.55–0.69。
--contrast 不检查饱和度和 R−B；那两项仍在默认 A 档、--dark、--outdoor 里。
--dark 是 §9.1 B 档，阈值与改前脚本相同。
--outdoor 是 §12A.2，阈值与改前脚本相同。
三种模式互斥。

色调仍先缩到 400×400 再计算，和本脚本改前一致。
UTA §6F.1 与 §9 写的是 200×200。两套下采样的数字不一定相同。
本次不改边长，避免把未要求的口径变化写进既有验收。

--slot 检查原始像素，不看 400×400：
  G1     2000×2000，并检查最外一圈像素全部为 RGB 255,255,255
  S      1600×2000
  AP-PC  1464×600，或母版 2928×1200
  AP-M   600×450，或母版 1200×900
AGENTS §0.4 的 2508×2508、2000×2500 是高清目标，不是本旗标的通过尺寸。

任意一项越界，退出码为 1。用法错误或文件打不开，退出码为 2。
--json 时把同一结论打到 stdout。

不能判断，也不要当成已经判断：字体、错字、产品外形、表情、「能联想到」。
纯色底和白底图不适合用生活场景色调区间解释。白底主图用 --slot G1，不要加 --contrast。
"""
import json
import sys

import numpy as np
from PIL import Image

# 生活场景 A 档（UTA §9.1）。p5 上限 0.12 来自 §6F 与 D3；
# 历史区间 0.12–0.24 不再当作下限。
A = {
    "L_mean": (0.55, 0.69),
    "L_std": (0.22, 0.28),
    "p5": (None, 0.12),
    "p95": (0.88, 0.97),
    "sat": (0.22, 0.30),
    "warm_RminusB": (0.07, 0.15),
}
# 暗场科技/夜景（第 9.1 节 B 模式）。与改前脚本相同。
D = {
    "L_mean": (0.26, 0.37),
    "L_std": (0.18, 0.27),
    "p5": (0.04, 0.09),
    "p95": (0.55, 0.75),
    "sat": (0.37, 0.60),
    "warm_RminusB": (0.06, 0.23),
}
# 户外场景（第 12A.2 节）。p5 只设下限，p95 只设上限。与改前脚本相同。
O = {
    "L_mean": (0.50, 0.70),
    "L_std": (0.22, 0.30),
    "p5": (0.12, None),
    "p95": (None, 0.97),
    "sat": (0.22, 0.40),
    "warm_RminusB": (-0.02, 0.10),
}
SLOT_SIZES = {
    "G1": ((2000, 2000),),
    "S": ((1600, 2000),),
    "AP-PC": ((1464, 600), (2928, 1200)),
    "AP-M": ((600, 450), (1200, 900)),
}


def flag_bounds(lo, hi, x):
    if (lo is None or x >= lo) and (hi is None or x <= hi):
        return ""
    if lo is None:
        return f"(!≤{hi})"
    if hi is None:
        return f"(!≥{lo})"
    return f"(!{lo}–{hi})"


def luminance_metrics(path):
    image = Image.open(path).convert("RGB")
    size = image.size
    sample = np.asarray(image.resize((400, 400))).astype(float) / 255
    r, g, b = sample[..., 0], sample[..., 1], sample[..., 2]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    mx, mn = sample.max(2), sample.min(2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    values = {
        "L_mean": float(lum.mean()),
        "L_std": float(lum.std()),
        "p5": float(np.percentile(lum, 5)),
        "p95": float(np.percentile(lum, 95)),
        "sat": float(sat.mean()),
        "warm_RminusB": float((r - b).mean()),
        "span_p95_minus_p5": float(np.percentile(lum, 95) - np.percentile(lum, 5)),
        "dark_fraction_L_lt_0_2": float((lum < 0.2).mean()),
    }
    return image, size, values


def contrast_flags(values):
    """§6F。只返回越界项名称。"""
    flags = []
    if not 0.55 <= values["L_mean"] <= 0.69:
        flags.append("L_mean")
    if values["L_std"] < 0.25:
        flags.append("L_std")
    if values["p5"] > 0.12:
        flags.append("p5")
    if values["span_p95_minus_p5"] < 0.80:
        flags.append("span_p95_minus_p5")
    dark = values["dark_fraction_L_lt_0_2"]
    if dark < 0.10 or dark > 0.20:
        flags.append("dark_fraction_L_lt_0_2")
    return flags


def band_flags(bounds, values):
    flags = []
    for key, (lo, hi) in bounds.items():
        if flag_bounds(lo, hi, values[key]):
            flags.append(key)
    return flags


def edge_is_pure_white(image):
    """最外一圈像素全部为 RGB 255。用原始图，不使用 400×400 缩图。"""
    rgb = np.asarray(image.convert("RGB"))
    top = rgb[0, :, :]
    bottom = rgb[-1, :, :]
    left = rgb[:, 0, :]
    right = rgb[:, -1, :]
    edge = np.concatenate((top, bottom, left, right), axis=0)
    return bool(np.all(edge == 255))


def check_slot(slot, size, image):
    allowed = SLOT_SIZES[slot]
    size_ok = size in allowed
    white_ok = None
    notes = []
    if not size_ok:
        want = " 或 ".join(f"{w}×{h}" for w, h in allowed)
        notes.append(f"size {size[0]}×{size[1]} (!{want})")
    if slot == "G1":
        white_ok = edge_is_pure_white(image)
        if not white_ok:
            notes.append("white_edge (!RGB 255)")
    return size_ok, white_ok, notes


def parse_args(argv):
    mode = "A"
    mode_flags = []
    as_json = False
    slot = None
    files = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--json":
            as_json = True
        elif arg in ("--dark", "--outdoor", "--contrast"):
            mode_flags.append(arg)
        elif arg == "--slot":
            if i + 1 >= len(argv):
                return None, "缺少 --slot 的值"
            slot = argv[i + 1]
            i += 1
            if slot not in SLOT_SIZES:
                return None, f"未知图位 {slot}；只能是 G1、S、AP-PC、AP-M"
        elif arg.startswith("-"):
            return None, f"未知参数 {arg}"
        else:
            files.append(arg)
        i += 1
    if len(mode_flags) > 1:
        return None, " --dark、--outdoor、--contrast 只能选一个"
    if mode_flags == ["--dark"]:
        mode = "dark"
    elif mode_flags == ["--outdoor"]:
        mode = "outdoor"
    elif mode_flags == ["--contrast"]:
        mode = "contrast"
    if not files:
        return None, "没有图片路径"
    return {"mode": mode, "json": as_json, "slot": slot, "files": files}, None


def evaluate(path, mode, slot):
    image, size, values = luminance_metrics(path)
    # 白底主图不是生活场景。只写 --slot G1 时不套用 A 档色调。
    # 调用方如果明确加了 --contrast / --dark / --outdoor，色调检查仍然执行。
    skip_tone = slot == "G1" and mode == "A"
    if skip_tone:
        flags = []
        shown = []
    elif mode == "contrast":
        flags = contrast_flags(values)
        shown = [
            "L_mean",
            "L_std",
            "p5",
            "p95",
            "span_p95_minus_p5",
            "dark_fraction_L_lt_0_2",
        ]
    else:
        bounds = {"A": A, "dark": D, "outdoor": O}[mode]
        flags = band_flags(bounds, values)
        shown = list(bounds)
    size_ok = None
    white_ok = None
    slot_notes = []
    if slot:
        size_ok, white_ok, slot_notes = check_slot(slot, size, image)
        if size_ok is False:
            flags.append("size")
        if white_ok is False:
            flags.append("white_edge")
    text_parts = []
    for key in shown:
        mark = ""
        if key in flags:
            if mode == "contrast":
                mark = "(!§6F)"
            else:
                bounds = {"A": A, "dark": D, "outdoor": O}[mode]
                mark = flag_bounds(*bounds[key], values[key])
        text_parts.append(f"{key}={values[key]:.3f}{mark}")
    text_parts.extend(slot_notes)
    return {
        "file": path,
        "width": size[0],
        "height": size[1],
        "metrics": {key: round(values[key], 6) for key in values},
        "flags": flags,
        "size_ok": size_ok,
        "white_edge_ok": white_ok,
        "pass": not flags,
        "tone_skipped": bool(skip_tone),
        "text": path + " " + (" ".join(text_parts) if text_parts else "tone=skipped_white_main"),
    }


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parsed, error = parse_args(argv)
    if error:
        print(error, file=sys.stderr)
        if argv and "--json" in argv:
            print(json.dumps({"pass": False, "error": error}, ensure_ascii=False))
        return 2
    results = []
    try:
        for path in parsed["files"]:
            results.append(evaluate(path, parsed["mode"], parsed["slot"]))
    except (OSError, ValueError) as exc:
        message = f"无法读取图片：{exc}"
        print(message, file=sys.stderr)
        if parsed["json"]:
            print(json.dumps({"pass": False, "error": message}, ensure_ascii=False))
        return 2
    passed = all(item["pass"] for item in results)
    payload = {
        "mode": parsed["mode"],
        "slot": parsed["slot"],
        "sample": "400x400",
        "sample_note": "UTA §6F.1 与 §9 写 200×200；本脚本保持改前的 400×400。",
        "cannot_judge": ["字体", "错字", "产品外形", "表情", "能联想到"],
        "pass": passed,
        "results": results,
    }
    if parsed["json"]:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        for item in results:
            print(item["text"])
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
