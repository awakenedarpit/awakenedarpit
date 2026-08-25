#!/usr/bin/env python3
"""Create a Gargi-guide-style dot-matrix portrait SVG."""
import argparse
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def equalize_masked(gray, mask):
    hist = [0] * 256
    total = 0
    for g, a in zip(gray.getdata(), mask.getdata()):
        if a > 8:
            hist[g] += 1
            total += 1
    if not total:
        return gray
    cdf, run = [], 0
    for n in hist:
        run += n
        cdf.append(run)
    first = next(v for v in cdf if v)
    den = max(1, total - first)
    lut = [round(max(0, v - first) * 255 / den) for v in cdf]
    return gray.point(lut)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("image")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--cols", type=int, default=88)
    p.add_argument("--equalize", action="store_true")
    p.add_argument("--detail", type=float, default=0.0)
    p.add_argument("--color", action="store_true")
    p.add_argument("--reveal", action="store_true")
    p.add_argument("--reveal-time", type=float, default=2.5)
    p.add_argument("--reveal-fade", type=float, default=0.45)
    p.add_argument("--reveal-dir", choices=["down", "up"], default="down")
    p.add_argument("--circle", action="store_true")
    p.add_argument("--square", action="store_true")
    p.add_argument("--focus", nargs=2, type=float, default=(0.5, 0.5))
    p.add_argument("--invert", action="store_true")
    args = p.parse_args()

    raw = ImageOps.exif_transpose(Image.open(args.image).convert("RGBA"))
    w, h = raw.size
    if args.square or args.circle:
        s = min(w, h)
        fx, fy = args.focus
        cx, cy = fx * w, fy * h
        left = max(0, min(w - s, int(cx - s / 2)))
        top = max(0, min(h - s, int(cy - s / 2)))
        raw = raw.crop((left, top, left + s, top + s))

    alpha = raw.getchannel("A")
    rgb = raw.convert("RGB")
    gray = ImageOps.grayscale(rgb)
    if args.equalize:
        gray = equalize_masked(gray, alpha)
    if args.detail:
        gray = ImageEnhance.Contrast(gray).enhance(1 + 0.45 * args.detail)
        gray = gray.filter(ImageFilter.UnsharpMask(radius=1.0, percent=int(100 + 160 * args.detail), threshold=2))
    if args.invert:
        gray = ImageOps.invert(gray)

    cols = max(20, args.cols)
    cell = 10
    g = gray.resize((cols, cols), Image.Resampling.LANCZOS)
    a = alpha.resize((cols, cols), Image.Resampling.LANCZOS)
    c = rgb.resize((cols, cols), Image.Resampling.LANCZOS)
    rows = [[] for _ in range(cols)]

    for y in range(cols):
        for x in range(cols):
            av = a.getpixel((x, y)) / 255
            if av < 0.08:
                continue
            value = max(0.035, (g.getpixel((x, y)) / 255) * av)
            if args.color:
                r, gg, b = c.getpixel((x, y))
                lift = 0.08 * value
                r = round(r + (255 - r) * lift)
                gg = round(gg + (255 - gg) * lift)
                b = round(b + (255 - b) * lift)
                fill = f"rgb({r},{gg},{b})"
            else:
                fill = "#39d353"
            radius = 1.15 + 2.35 * (value ** 0.62)
            rows[y].append((x * cell + cell / 2, y * cell + cell / 2, radius, fill))

    out = Path(args.output)
    if out.suffix.lower() != ".svg":
        out = out.with_suffix(".svg")
    out.parent.mkdir(parents=True, exist_ok=True)

    defs = []
    clip_attr = ""
    if args.circle:
        defs.append(f'<clipPath id="circle"><circle cx="{cols*cell/2}" cy="{cols*cell/2}" r="{cols*cell/2}"/></clipPath>')
        clip_attr = ' clip-path="url(#circle)"'
    if args.reveal:
        animation = "revealUp" if args.reveal_dir == "up" else "revealDown"
        defs.append(f'<style>@keyframes {animation}{{from{{opacity:0}}to{{opacity:1}}}}.row{{opacity:0;animation:{animation} {args.reveal_fade}s ease-out forwards}}</style>')
    else:
        defs.append('<style>.row{opacity:1}</style>')

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {cols*cell} {cols*cell}" role="img" aria-label="Arpit Raj dot-matrix portrait"><defs>', ''.join(defs), '</defs>', f'<g{clip_attr}>']
    for y, dots in enumerate(rows):
        delay = (y / max(1, cols - 1)) * max(0.01, args.reveal_time - args.reveal_fade) if args.reveal else 0
        svg.append(f'<g class="row" style="animation-delay:{delay:.3f}s">')
        for cx, cy, r, fill in dots:
            svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.2f}" fill="{fill}"/>')
        svg.append('</g>')
    svg.append('</g></svg>')
    out.write_text("\n".join(svg), encoding="utf-8")


if __name__ == "__main__":
    main()
