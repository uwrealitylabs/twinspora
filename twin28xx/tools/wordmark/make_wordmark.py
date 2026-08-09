#!/usr/bin/env python3
"""Generate the twin28xx back-silkscreen wordmark and write it into the board.

"twin" is set in Instrument Serif Italic, "28xx" in Pressuru. Both are converted
to filled polygons on B.SilkS, so the board carries no font dependency.

    ./make_wordmark.py --preview wm.png     # render a PNG, touch nothing
    ./make_wordmark.py --apply              # write into twin28xx.kicad_pcb
    ./make_wordmark.py --apply --remove     # strip the wordmark back out

Re-running --apply replaces the previous wordmark, so tweak CONFIG and re-run
as often as you like. Needs fonttools; --preview also needs Pillow.
"""
import argparse
import hashlib
import math
import os
import re
import shutil
import sys

from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont

# --------------------------------------------------------------------------
# CONFIG — the knobs. Sizes in mm.
# --------------------------------------------------------------------------
CONFIG = dict(
    em_mm=6.467,       # type size. Everything scales from this.
                       # 23.9mm wide is the ceiling for the space on the back;
                       # raising num_sx costs em_mm to stay inside it.

    # Per-run stretch. sx < 1 condenses (skinnier), sx > 1 expands (fatter).
    # sy scales about the baseline, so both runs stay on the same line.
    twin_sx=1.00,      # "twin"  horizontal
    twin_sy=1.25,      # "twin"  vertical   -> taller, reads skinnier
    num_sx=1.00,       # "28xx"  horizontal -> wider, reads fatter
    num_sy=1.00,       # "28xx"  vertical

    gap_em=0.10,       # space between "twin" and "28xx", in em
    track_twin=0.0,    # extra letterspacing within each run, in em
    track_num=0.0,

    # Pressuru's size relative to Instrument Serif. With match_xheight=True it is
    # derived at run time so Pressuru's 'x' is exactly as tall as the italic 'n',
    # tracking twin_sy/num_sy automatically; that also lands the digits on the
    # italic's ascender line. Set match_xheight=False to use pressuru_rel as given.
    match_xheight=True,
    pressuru_rel=0.516 / 0.650,

    center=(95.575, 108.404),   # wordmark centre on the board, mm
    mirror=True,                # B.SilkS artwork must be mirrored in X
    layer='B.SilkS',
    simplify_mm=0.005,          # outline simplification tolerance
)

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, 'fonts')
PCB = os.path.normpath(os.path.join(HERE, '..', '..', 'twin28xx.kicad_pcb'))
GROUP_NAME = 'twin28xx wordmark'
TAIL = '\t(embedded_fonts no)\n)'


# --------------------------------------------------------------------------
# glyph outlines
# --------------------------------------------------------------------------
class _FlattenPen(BasePen):
    """Collect contours as polylines, subdividing curves to a flatness tolerance."""

    def __init__(self, glyphSet, tol):
        super().__init__(glyphSet)
        self.tol = tol
        self.contours = []
        self._cur = None

    def _moveTo(self, pt):
        self._cur = [pt]

    def _lineTo(self, pt):
        self._cur.append(pt)

    def _curveToOne(self, p1, p2, p3):
        p0 = self._cur[-1]
        d = math.dist(p0, p1) + math.dist(p1, p2) + math.dist(p2, p3)
        n = max(4, min(96, int(math.sqrt(d / max(self.tol, 1e-6)) * 1.6)))
        for i in range(1, n + 1):
            t = i / n
            u = 1 - t
            self._cur.append((
                u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))

    def _closePath(self):
        if self._cur and len(self._cur) > 2:
            if self._cur[0] == self._cur[-1]:
                self._cur.pop()
            self.contours.append(self._cur)
        self._cur = None

    _endPath = _closePath


def _signed_area(c):
    a = 0.0
    for i in range(len(c)):
        x0, y0 = c[i]
        x1, y1 = c[(i + 1) % len(c)]
        a += x0 * y1 - x1 * y0
    return a / 2.0


class Face:
    def __init__(self, filename):
        self.tt = TTFont(os.path.join(FONTS, filename))
        self.upem = self.tt['head'].unitsPerEm
        self.gs = self.tt.getGlyphSet()
        self.cmap = self.tt.getBestCmap()
        self.hmtx = self.tt['hmtx']
        self.kern = self._kerning()

    def _g(self, ch):
        return self.cmap[ord(ch)]

    def advance(self, ch):
        return self.hmtx[self._g(ch)][0] / self.upem

    def contours(self, ch, tol_em=0.0004):
        pen = _FlattenPen(self.gs, tol_em * self.upem)
        self.gs[self._g(ch)].draw(pen)
        pen._closePath()
        return [[(x / self.upem, y / self.upem) for x, y in c] for c in pen.contours]

    def _kerning(self):
        pairs = {}
        if 'GPOS' not in self.tt:
            return pairs
        try:
            for lookup in self.tt['GPOS'].table.LookupList.Lookup:
                if lookup.LookupType != 2:
                    continue
                for st in lookup.SubTable:
                    fmt = getattr(st, 'Format', None)
                    if fmt == 1:
                        for gi, ps in enumerate(st.PairSet):
                            for rec in ps.PairValueRecord:
                                v = getattr(rec.Value1, 'XAdvance', 0) or 0
                                if v:
                                    pairs[(st.Coverage.glyphs[gi], rec.SecondGlyph)] = v / self.upem
                    elif fmt == 2:
                        c1, c2 = st.ClassDef1.classDefs, st.ClassDef2.classDefs
                        for g1 in st.Coverage.glyphs:
                            for g2, k2 in c2.items():
                                rec = st.Class1Record[c1.get(g1, 0)].Class2Record[k2]
                                v = getattr(rec.Value1, 'XAdvance', 0) or 0
                                if v:
                                    pairs[(g1, g2)] = v / self.upem
        except Exception:
            pass
        return pairs

    def kerning(self, a, b):
        return self.kern.get((self._g(a), self._g(b)), 0.0)


# --------------------------------------------------------------------------
# composition
# --------------------------------------------------------------------------
def _glyph_top(face, ch):
    return max(p[1] for c in face.contours(ch) for p in c)


def pressuru_rel(cfg, twin, num):
    """Pressuru size relative to Instrument Serif.

    When matching, solve for the ratio that renders Pressuru's 'x' at exactly the
    height of the italic 'n', after each run's own sy is applied.
    """
    if not cfg.get('match_xheight', True):
        return cfg['pressuru_rel']
    return (_glyph_top(twin, 'n') * cfg['twin_sy']) / (_glyph_top(num, 'x') * cfg['num_sy'])


def compose(cfg):
    """-> list of (contour, is_hole) in mm, Y-up, baseline at y=0, starting at x=0."""
    twin = Face('InstrumentSerif-Italic.ttf')
    num = Face('Pressuru.ttf')
    em = cfg['em_mm']
    rel = pressuru_rel(cfg, twin, num)
    runs = [("twin", twin, 1.0, cfg['track_twin'], cfg['twin_sx'], cfg['twin_sy']),
            ("28xx", num, rel, cfg['track_num'], cfg['num_sx'], cfg['num_sy'])]
    out = []
    x = 0.0
    for ri, (text, face, rel, track, sx, sy) in enumerate(runs):
        if ri:
            x += cfg['gap_em'] * em
        s = em * rel
        for i, ch in enumerate(text):
            if i:
                x += (face.kerning(text[i - 1], ch) * s + track * em) * sx
            for c in face.contours(ch):
                out.append(([(px * s * sx + x, py * s * sy) for px, py in c],
                            _signed_area(c) > 0))
            x += face.advance(ch) * s * sx
    return out


def bbox(contours):
    pts = [p for c, _ in contours for p in c]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def place(contours, cfg):
    """Font space (Y-up) -> board space (Y-down), centred, mirrored for the back."""
    x0, y0, x1, y1 = bbox(contours)
    xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
    cx, cy = cfg['center']
    sx = -1.0 if cfg['mirror'] else 1.0
    return [([(cx + sx * (px - xm), cy - (py - ym)) for px, py in c], hole)
            for c, hole in contours]


# --------------------------------------------------------------------------
# holes -> single outlines (KiCad gr_poly takes one closed ring)
# --------------------------------------------------------------------------
def _point_in(poly, pt):
    x, y = pt
    inside = False
    for i in range(len(poly)):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % len(poly)]
        if (y0 > y) != (y1 > y) and x0 + (y - y0) * (x1 - x0) / (y1 - y0) > x:
            inside = not inside
    return inside


def keyhole(contours):
    outers = [list(c) for c, h in contours if not h]
    holes = [list(c) for c, h in contours if h]
    buckets = [[] for _ in outers]
    for hl in holes:
        cands = [k for k, o in enumerate(outers) if _point_in(o, hl[0])]
        if cands:
            buckets[min(cands, key=lambda k: abs(_signed_area(outers[k])))].append(hl)
    rings = []
    for o, hs in zip(outers, buckets):
        for hl in sorted(hs, key=lambda h: -abs(_signed_area(h))):
            best = min(((i, j) for i in range(len(o)) for j in range(len(hl))),
                       key=lambda ij: (o[ij[0]][0] - hl[ij[1]][0]) ** 2 +
                                      (o[ij[0]][1] - hl[ij[1]][1]) ** 2)
            i, j = best
            o = o[:i + 1] + hl[j:] + hl[:j + 1] + o[i:]
        rings.append(o)
    return rings


# --------------------------------------------------------------------------
# simplification
# --------------------------------------------------------------------------
def _rdp(pts, tol):
    if len(pts) < 3:
        return list(pts)
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        worst, wi = -1.0, -1
        ax, ay = pts[i]
        bx, by = pts[j]
        dx, dy = bx - ax, by - ay
        d2 = dx * dx + dy * dy
        for k in range(i + 1, j):
            px, py = pts[k]
            t = 0.0 if d2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / d2))
            d = math.hypot(px - ax - t * dx, py - ay - t * dy)
            if d > worst:
                worst, wi = d, k
        if worst > tol:
            keep[wi] = True
            stack += [(i, wi), (wi, j)]
    return [p for p, k in zip(pts, keep) if k]


def simplify(ring, tol):
    if len(ring) < 4:
        return list(ring)
    cx = sum(p[0] for p in ring) / len(ring)
    cy = sum(p[1] for p in ring) / len(ring)
    k = max(range(len(ring)), key=lambda i: (ring[i][0] - cx) ** 2 + (ring[i][1] - cy) ** 2)
    rot = ring[k:] + ring[:k]
    out = _rdp(rot + [rot[0]], tol)
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out


# --------------------------------------------------------------------------
# KiCad emit / patch
# --------------------------------------------------------------------------
def _uuid(seed):
    h = hashlib.sha1(seed.encode()).hexdigest()
    return f"{h[0:8]}-{h[8:12]}-4{h[13:16]}-8{h[17:20]}-{h[20:32]}"


def emit(rings, layer):
    blocks, uuids = [], []
    for n, ring in enumerate(rings):
        u = _uuid(f'twin28xx-poly-{n}')
        uuids.append(u)
        rows = ['\t\t\t' + ' '.join(f'(xy {x:.6f} {y:.6f})' for x, y in ring[i:i + 4])
                for i in range(0, len(ring), 4)]
        blocks.append('\t(gr_poly\n\t\t(pts\n' + '\n'.join(rows) + '\n\t\t)\n'
                      '\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type solid)\n\t\t)\n'
                      '\t\t(fill yes)\n'
                      f'\t\t(layer "{layer}")\n\t\t(uuid "{u}")\n\t)')
    members = ['\t\t\t' + ' '.join(f'"{u}"' for u in uuids[i:i + 2])
               for i in range(0, len(uuids), 2)]
    group = (f'\t(group "{GROUP_NAME}"\n\t\t(uuid "{_uuid("twin28xx-group")}")\n'
             '\t\t(members\n' + '\n'.join(members) + '\n\t\t)\n\t)')
    return '\n'.join(blocks) + '\n' + group


def strip(src):
    """Remove a previously written wordmark (group + its gr_poly members)."""
    m = re.search(r'\t\(group "%s".*?\n\t\)\n' % re.escape(GROUP_NAME), src, re.S)
    if not m:
        return src, 0
    uuids = re.findall(r'"([0-9a-fA-F-]{36})"', m.group(0))
    src = src[:m.start()] + src[m.end():]
    removed = 0
    for u in uuids:
        hit = re.search(r'\(uuid "%s"\)' % re.escape(u), src)
        if not hit:
            continue
        start = src.rfind('\t(gr_poly\n', 0, hit.start())
        end = src.find('\n\t)\n', hit.end())
        if start == -1 or end == -1:
            continue
        src = src[:start] + src[end + 4:]
        removed += 1
    return src, removed


def build_rings(cfg):
    contours = compose(cfg)
    w, h = bbox(contours)[2] - bbox(contours)[0], bbox(contours)[3] - bbox(contours)[1]
    rings = keyhole(place(contours, cfg))
    return [simplify(r, cfg['simplify_mm']) for r in rings], (w, h)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--apply', action='store_true', help='write into the .kicad_pcb')
    ap.add_argument('--remove', action='store_true', help='with --apply: strip and stop')
    ap.add_argument('--preview', metavar='PNG', help='render a preview image')
    ap.add_argument('--pcb', default=PCB)
    ap.add_argument('--no-backup', action='store_true')
    for k in ('em_mm', 'twin_sx', 'twin_sy', 'num_sx', 'num_sy', 'gap_em'):
        ap.add_argument('--' + k.replace('_', '-'), type=float, help=f'override {k}')
    args = ap.parse_args()

    cfg = dict(CONFIG)
    for k in ('em_mm', 'twin_sx', 'twin_sy', 'num_sx', 'num_sy', 'gap_em'):
        v = getattr(args, k)
        if v is not None:
            cfg[k] = v

    rings, (w, h) = build_rings(cfg)
    npts = sum(len(r) for r in rings)
    print(f'wordmark {w:.2f} x {h:.2f} mm  |  {len(rings)} polygons, {npts} points')
    print(f'  em {cfg["em_mm"]}mm  twin {cfg["twin_sx"]}x/{cfg["twin_sy"]}y  '
          f'28xx {cfg["num_sx"]}x/{cfg["num_sy"]}y  centre {cfg["center"]}')

    if args.preview:
        from PIL import Image, ImageDraw
        S, pad = 90, 1.0
        xs = [p[0] for r in rings for p in r]
        ys = [p[1] for r in rings for p in r]
        W = int((max(xs) - min(xs) + 2 * pad) * S)
        H = int((max(ys) - min(ys) + 2 * pad) * S)
        img = Image.new('RGB', (W, H), (16, 18, 22))
        d = ImageDraw.Draw(img)
        # mirrored back on screen = what you see looking at the back of the board
        for r in rings:
            d.polygon([((max(xs) - p[0] + pad) * S, (p[1] - min(ys) + pad) * S) for p in r],
                      fill=(238, 238, 238))
        img.save(args.preview)
        print(f'  preview -> {args.preview}')

    if not args.apply:
        return 0

    src = open(args.pcb).read()
    src, removed = strip(src)
    if removed:
        print(f'  removed {removed} existing wordmark polygons')
    if not args.remove:
        if TAIL not in src:
            print('ERROR: insertion point not found at end of board file', file=sys.stderr)
            return 1
        src = src.replace(TAIL, emit(rings, cfg['layer']) + '\n' + TAIL)
    if not args.no_backup:
        shutil.copy2(args.pcb, args.pcb + '.bak')
        print(f'  backup -> {os.path.basename(args.pcb)}.bak')
    open(args.pcb, 'w').write(src)
    print(f'  {"removed from" if args.remove else "written into"} {args.pcb}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
