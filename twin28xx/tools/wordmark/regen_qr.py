#!/usr/bin/env python3
"""Regenerate the back-silkscreen QR code in place.

Replaces the fp_poly artwork inside the QR `LOGO` footprint with a freshly
encoded symbol, keeping the same position, size and module count so it drops
straight into the existing spot.

    ./regen_qr.py --url https://github.com/uwrealitylabs/twin28xx --preview qr.png
    ./regen_qr.py --url https://github.com/uwrealitylabs/twin28xx --apply

Verify the result with an actual scanner before trusting it; `--preview` writes a
PNG suitable for `swift qrread.swift`.
"""
import argparse
import hashlib
import math
import os
import re
import shutil
import sys

import numpy as np

import qr
from trace import contours, signed_area
import make_wordmark as MW
from sexp_min import parse, sym, val, find, findall

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.normpath(os.path.join(HERE, '..', '..', 'twin28xx.kicad_pcb'))
FP_ANCHOR = (134.2, 126.5)        # the QR LOGO footprint's translate
LAYER = 'B.SilkS'


def find_qr_footprint(src):
    """-> (start, end, translate, rotate) span of the QR LOGO footprint block."""
    for m in re.finditer(r'\n\t\(footprint "LOGO"\n', src):
        end = src.index('\n\t)\n', m.start())
        block = src[m.start():end]
        t = re.search(r'\(translate ([\d.-]+) ([\d.-]+)\)', block)
        if not t:
            continue
        tx, ty = float(t.group(1)), float(t.group(2))
        if abs(tx - FP_ANCHOR[0]) < 0.01 and abs(ty - FP_ANCHOR[1]) < 0.01:
            r = re.search(r'\(rotate ([\d.-]+)\)', block)
            return m.start() + 1, end + len('\n\t)\n'), (tx, ty), float(r.group(1)) if r else 0.0
    raise SystemExit('QR LOGO footprint not found')


def existing_extent(src, start, end, translate, rotate):
    """Ink bbox of the footprint's current fp_poly artwork, in board mm."""
    block = src[start:end]
    tree = parse(block)
    pts = []
    for p in findall(tree, 'fp_poly'):
        for q in findall(find(p, 'pts'), 'xy'):
            lx, ly = float(q[1]), float(q[2])
            a = math.radians(rotate)
            ca, sa = math.cos(a), math.sin(a)
            pts.append((translate[0] + lx * ca + ly * sa,
                        translate[1] - lx * sa + ly * ca))
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys), len(findall(tree, 'fp_poly'))


def grid_to_local(grid, x0, y0, pitch, translate, rotate, mirror=True):
    """Module grid (readable orientation) -> merged polygons in footprint-local mm."""
    n = len(grid)
    board = np.zeros((n, n), bool)
    for r in range(n):
        for c in range(n):
            board[r][c] = grid[r][n - 1 - c] if mirror else grid[r][c]

    rings_px = contours(board)
    rings = []
    for ring in rings_px:
        mm = [(x0 + (px + 0.5) * pitch, y0 + (py + 0.5) * pitch) for px, py in ring]
        rings.append(mm)
    outers = [r for r in rings if signed_area(r) < 0]
    holes = [r for r in rings if signed_area(r) > 0]
    merged = MW.keyhole([(r, False) for r in outers] + [(r, True) for r in holes])

    a = math.radians(-rotate)
    ca, sa = math.cos(a), math.sin(a)
    out = []
    for ring in merged:
        loc = []
        for bx, by in ring:
            dx, dy = bx - translate[0], by - translate[1]
            loc.append((dx * ca + dy * sa, -dx * sa + dy * ca))
        out.append(loc)
    return out, len(outers), len(holes)


def emit_fp_polys(rings, layer=LAYER):
    blocks = []
    for i, ring in enumerate(rings):
        u = hashlib.sha1(f'twin28xx-qr-{i}'.encode()).hexdigest()
        uu = f"{u[0:8]}-{u[8:12]}-4{u[13:16]}-8{u[17:20]}-{u[20:32]}"
        rows = ['\t\t\t\t' + ' '.join(f'(xy {x:.6f} {y:.6f})' for x, y in ring[j:j + 6])
                for j in range(0, len(ring), 6)]
        blocks.append('\t\t(fp_poly\n\t\t\t(pts\n' + '\n'.join(rows) + '\n\t\t\t)\n'
                      '\t\t\t(stroke\n\t\t\t\t(width 0)\n\t\t\t\t(type solid)\n\t\t\t)\n'
                      '\t\t\t(fill yes)\n'
                      f'\t\t\t(layer "{layer}")\n\t\t\t(uuid "{uu}")\n\t\t)')
    return '\n'.join(blocks)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--url', required=True)
    ap.add_argument('--level', default='Q', choices=list(qr.LEVELS))
    ap.add_argument('--version', type=int, default=None,
                    help='force a QR version; default matches the existing symbol')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--preview', metavar='PNG')
    ap.add_argument('--pcb', default=PCB)
    ap.add_argument('--no-backup', action='store_true')
    args = ap.parse_args()

    src = open(args.pcb).read()
    start, end, translate, rotate = find_qr_footprint(src)
    x0, y0, x1, y1, npoly = existing_extent(src, start, end, translate, rotate)
    side = max(x1 - x0, y1 - y0)
    print(f'existing QR: {npoly} polygons, {side:.3f} mm square at '
          f'({x0:.3f},{y0:.3f})-({x1:.3f},{y1:.3f})')

    data = args.url.encode()
    version = args.version
    if version is None:
        version = 4          # existing symbol is 33x33
        while qr.capacity(version, args.level) < len(data) + 2:
            version += 1
    grid, version, level, mask = qr.encode(data, version=version, level=args.level)
    n = len(grid)
    pitch = side / n
    print(f'new QR: V{version}-{level} mask={mask}, {n}x{n} modules, '
          f'pitch {pitch*1000:.1f} um, payload {len(data)} bytes')

    if args.preview:
        from PIL import Image
        S, q = 12, 4
        img = Image.new('L', ((n + 2 * q) * S,) * 2, 255)
        px = img.load()
        for r in range(n):
            for c in range(n):
                if grid[r][c]:
                    for i in range(S):
                        for j in range(S):
                            px[(c + q) * S + j, (r + q) * S + i] = 0
        img.save(args.preview)
        print(f'  preview -> {args.preview}')

    rings, nout, nhole = grid_to_local(grid, x0, y0, pitch, translate, rotate)
    print(f'  traced {nout} outlines + {nhole} holes -> {len(rings)} polygons, '
          f'{sum(len(r) for r in rings)} points')

    if not args.apply:
        return 0

    block = src[start:end]
    first = block.index('\t\t(fp_poly')
    last = block.rindex('\t\t)\n') + len('\t\t)\n')
    newblock = block[:first] + emit_fp_polys(rings) + '\n' + block[last:]
    out = src[:start] + newblock + src[end:]
    if not args.no_backup:
        shutil.copy2(args.pcb, args.pcb + '.bak')
    open(args.pcb, 'w').write(out)
    print(f'  replaced {npoly} fp_poly with {len(rings)} in {os.path.basename(args.pcb)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
