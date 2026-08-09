#!/usr/bin/env python3
"""Knock the back-silkscreen text out of the twin28xx wordmark.

Where a designator or the bible verse is covered by the wordmark, the wordmark
is the only thing printed, so the text vanishes into it. This computes the
symmetric difference (wordmark XOR text): overlapping ink is removed from both,
leaving the text reading dark-on-white inside the wordmark and white-on-dark
outside it.

    ./knockout.py --preview ko.png     # render only
    ./knockout.py --apply              # rewrite the wordmark polygons
    ./knockout.py --apply --remove     # undo, restoring the plain wordmark

Any text item that touches the wordmark is converted to polygons in full (not
just its covered part), so there is no seam where it crosses the edge. The
original text is hidden, and `--remove` unhides it.
"""
import argparse
import json
import math
import os
import re
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw

from kicad_text import StrokeFont, effective_pen
from trace import contours, signed_area
import make_wordmark as MW

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.normpath(os.path.join(HERE, '..', '..', 'twin28xx.kicad_pcb'))
STATE = os.path.join(HERE, 'knockout_state.json')
GROUP_NAME = 'twin28xx wordmark'
LAYER = 'B.SilkS'

RES = 150.0          # px per mm for the boolean raster (~6.7 um)
SIMPLIFY_MM = 0.010  # outline simplification after tracing
GROW_MM = 0.0        # dilate text before the XOR; widens the knockout slot


# ---------------------------------------------------------------- board access
sys.path.insert(0, os.path.join(HERE))


def _sexp():
    """The scratch parser lives beside this file; keep imports lazy and local."""
    from sexp_min import parse, sym, val, find, findall
    return parse, sym, val, find, findall


def load_wordmark(src, parse, sym, val, find, findall):
    m = re.search(r'\(group "%s".*?\(members(.*?)\)\n' % re.escape(GROUP_NAME), src, re.S)
    if not m:
        return [], set()
    uuids = set(re.findall(r'"([0-9a-fA-F-]{36})"', m.group(1)))
    tree = parse(src)
    polys = []
    for n in tree:
        if isinstance(n, list) and sym(n) == 'gr_poly':
            u = find(n, 'uuid')
            if u and val(u[1]) in uuids:
                p = find(n, 'pts')
                polys.append([(float(q[1]), float(q[2])) for q in findall(p, 'xy')])
    return polys, uuids


def rot(x, y, deg):
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    return x * ca + y * sa, -x * sa + y * ca


def text_items(tree, sym, val, find, layer=LAYER):
    """Stroke text on `layer`: top-level gr_text plus footprint properties."""
    out = []

    def eff(node):
        e = find(node, 'effects')
        sx = sy = 1.0
        th = 0.15
        italic = False
        jh, jv, mir = 'center', 'center', False
        if e:
            f = find(e, 'font')
            if f:
                s = find(f, 'size')
                if s:
                    sy, sx = float(s[1]), float(s[2])
                t = find(f, 'thickness')
                if t:
                    th = float(t[1])
                italic = bool(find(f, 'italic'))
            j = find(e, 'justify')
            if j:
                for tok in [val(x) for x in j[1:]]:
                    if tok in ('left', 'right'):
                        jh = tok
                    elif tok in ('top', 'bottom'):
                        jv = tok
                    elif tok == 'mirror':
                        mir = True
        return sx, sy, th, italic, jh, jv, mir

    for n in tree:
        if isinstance(n, list) and sym(n) == 'gr_text':
            ly = find(n, 'layer')
            if not ly or val(ly[1]) != layer or find(n, 'hide'):
                continue
            at = find(n, 'at')
            u = find(n, 'uuid')
            sx, sy, th, it, jh, jv, mir = eff(n)
            out.append(dict(kind='gr_text', uuid=val(u[1]) if u else None,
                            text=val(n[1]), at=(float(at[1]), float(at[2])),
                            angle=float(at[3]) if len(at) > 3 else 0.0,
                            size=(sx, sy), th=th, italic=it, jh=jh, jv=jv, mirror=mir))
        elif isinstance(n, list) and sym(n) == 'footprint':
            tr = find(n, 'transform')
            t = find(tr, 'translate')
            r = find(tr, 'rotate')
            fx, fy = float(t[1]), float(t[2])
            fang = float(r[1]) if r else 0.0
            for ch in n:
                if not (isinstance(ch, list) and sym(ch) in ('property', 'fp_text')):
                    continue
                ly = find(ch, 'layer')
                if not ly or val(ly[1]) != layer or find(ch, 'hide'):
                    continue
                txt = val(ch[2])
                if not txt:
                    continue
                at = find(ch, 'at')
                u = find(ch, 'uuid')
                x, y = rot(float(at[1]), float(at[2]), fang)
                sx, sy, th, it, jh, jv, mir = eff(ch)
                out.append(dict(kind=sym(ch), uuid=val(u[1]) if u else None,
                                text=txt, at=(fx + x, fy + y),
                                angle=float(at[3]) if len(at) > 3 else 0.0,
                                size=(sx, sy), th=th, italic=it, jh=jh, jv=jv, mirror=mir))
    return out


# ---------------------------------------------------------------- rasterising
class Raster:
    def __init__(self, x0, y0, x1, y1, res=RES):
        self.x0, self.y0, self.res = x0, y0, res
        self.W = int(math.ceil((x1 - x0) * res)) + 2
        self.H = int(math.ceil((y1 - y0) * res)) + 2

    def T(self, p):
        return ((p[0] - self.x0) * self.res + 1, (p[1] - self.y0) * self.res + 1)

    def inv(self, px, py):
        return (self.x0 + (px - 1) / self.res, self.y0 + (py - 1) / self.res)

    def blank(self):
        return Image.new('L', (self.W, self.H), 0)

    def polys(self, rings):
        img = self.blank()
        d = ImageDraw.Draw(img)
        for r in rings:
            d.polygon([self.T(p) for p in r], fill=255)
        return np.array(img) > 127

    def strokes(self, polylines, width):
        img = self.blank()
        d = ImageDraw.Draw(img)
        w = max(1, int(round(width * self.res)))
        r = w / 2
        for pl in polylines:
            P = [self.T(p) for p in pl]
            if len(P) > 1:
                d.line(P, fill=255, width=w, joint='curve')
            for x, y in (P[0], P[-1]):
                d.ellipse([x - r, y - r, x + r, y + r], fill=255)
        return np.array(img) > 127


def dilate(mask, r_px):
    out = mask
    for _ in range(int(r_px)):
        p = np.pad(out, 1, constant_values=False)
        out = out | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
    return out


# ---------------------------------------------------------------- main compute
def compute(src, grow_mm=GROW_MM, res=RES, simplify_mm=SIMPLIFY_MM, verbose=True):
    parse, sym, val, find, findall = _sexp()
    wm, wm_uuids = load_wordmark(src, parse, sym, val, find, findall)
    if not wm:
        raise SystemExit('no "%s" group found in the board' % GROUP_NAME)
    tree = parse(src)
    font = StrokeFont()

    pts = [p for r in wm for p in r]
    wx0, wy0 = min(p[0] for p in pts), min(p[1] for p in pts)
    wx1, wy1 = max(p[0] for p in pts), max(p[1] for p in pts)

    # which text touches the wordmark?
    coarse = Raster(wx0 - 1, wy0 - 1, wx1 + 1, wy1 + 1, res=20)
    WMc = coarse.polys(wm)
    touching = []
    for ti in text_items(tree, sym, val, find):
        th = effective_pen(ti['th'], ti['size'])
        pl = font.render(ti['text'], ti['at'], ti['size'], th, ti['angle'],
                         ti['jh'], ti['jv'], ti['mirror'], ti['italic'])
        if not pl:
            continue
        xs = [p[0] for s in pl for p in s]
        ys = [p[1] for s in pl for p in s]
        if max(xs) < wx0 - 1 or min(xs) > wx1 + 1 or max(ys) < wy0 - 1 or min(ys) > wy1 + 1:
            continue
        Tc = coarse.strokes(pl, th)
        if (Tc & WMc).any():
            ti['polylines'] = pl
            ti['pen'] = th
            touching.append(ti)

    if verbose:
        print(f'  wordmark polygons: {len(wm)}   text items touching: {len(touching)}')

    # full-resolution boolean over wordmark + touching text
    allx = [p[0] for r in wm for p in r] + [p[0] for t in touching for s in t['polylines'] for p in s]
    ally = [p[1] for r in wm for p in r] + [p[1] for t in touching for s in t['polylines'] for p in s]
    pad = 0.5
    R = Raster(min(allx) - pad, min(ally) - pad, max(allx) + pad, max(ally) + pad, res=res)
    if verbose:
        print(f'  raster {R.W}x{R.H} px @ {res:g} px/mm')

    W = R.polys(wm)
    T = np.zeros_like(W)
    for t in touching:
        T |= R.strokes(t['polylines'], t['pen'])
    if grow_mm > 0:
        T = dilate(T, round(grow_mm * res))

    result = W ^ T
    if verbose:
        print(f'  ink: wordmark {W.sum()/res/res:.1f} mm2, text {T.sum()/res/res:.2f} mm2, '
              f'result {result.sum()/res/res:.1f} mm2, removed {(W&T).sum()/res/res:.2f} mm2')

    rings_px = contours(result)
    rings = []
    for ring in rings_px:
        mm = [R.inv(x, y) for x, y in ring]
        mm = MW.simplify(mm, simplify_mm)
        if len(mm) >= 3:
            rings.append(mm)
    # trace() winds filled regions negative and holes positive (see its tests)
    outers = [r for r in rings if signed_area(r) < 0]
    holes = [r for r in rings if signed_area(r) > 0]
    if verbose:
        print(f'  traced {len(outers)} outlines + {len(holes)} holes, '
              f'{sum(len(r) for r in rings)} points')
    final = MW.keyhole([(r, False) for r in outers] + [(r, True) for r in holes])
    return dict(rings=final, wm_uuids=wm_uuids, touching=touching, wm=wm,
                result=result, raster=R, W=W, T=T)


# ---------------------------------------------------------------- board edits
def _block_bounds(src, uuid, heads):
    """Span of the top-level-ish block of one of `heads` containing this uuid."""
    m = re.search(r'\(uuid "%s"\)' % re.escape(uuid), src)
    if not m:
        return None
    start = max(src.rfind(h, 0, m.start()) for h in heads)
    if start < 0:
        return None
    indent = src[start:].split('(')[0]
    end = src.find('\n' + indent + ')\n', m.end())
    if end < 0:
        return None
    return start, end + len('\n' + indent + ')\n'), indent


def suppress(src, uuid):
    """Stop an item printing.

    Footprint properties support (hide yes). A gr_text does not, so it is cut out
    and its source stashed so --remove can put it back verbatim.
    """
    b = _block_bounds(src, uuid, ('\t\t(property ', '\t\t(fp_text ', '\t(gr_text '))
    if not b:
        return src, None
    start, end, indent = b
    block = src[start:end]
    if block.lstrip().startswith('(gr_text'):
        return src[:start] + src[end:], ('cut', block)
    m = re.search(r'\(uuid "%s"\)' % re.escape(uuid), src)
    ins = m.end()
    return src[:ins] + '\n' + indent + '\t(hide yes)' + src[ins:], ('hide', None)


def restore(src, records):
    n = 0
    for rec in records:
        if rec['how'] == 'hide':
            m = re.search(r'\(uuid "%s"\)\s*\n\s*\(hide yes\)' % re.escape(rec['uuid']), src)
            if m:
                src = src[:m.start()] + '(uuid "%s")' % rec['uuid'] + src[m.end():]
                n += 1
        else:
            if rec['uuid'] not in src:
                src = src.replace(MW.TAIL, rec['block'] + MW.TAIL)
                n += 1
    return src, n


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--remove', action='store_true')
    ap.add_argument('--preview', metavar='PNG')
    ap.add_argument('--pcb', default=PCB)
    ap.add_argument('--grow', type=float, default=GROW_MM,
                    help='dilate text before the XOR (mm); widens the knockout slot')
    ap.add_argument('--res', type=float, default=RES)
    ap.add_argument('--no-backup', action='store_true')
    args = ap.parse_args()

    src = open(args.pcb).read()

    if args.remove:
        if not os.path.exists(STATE):
            print('no knockout_state.json - nothing to undo', file=sys.stderr)
            return 1
        state = json.load(open(STATE))
        src, n = restore(src, state.get('suppressed', []))
        # put the pre-knockout wordmark back exactly as it was, including any
        # scaling done by hand in pcbnew (which exists only in these coordinates)
        wm = [[tuple(p) for p in r] for r in state.get('wordmark', [])]
        src, _ = MW.strip(src)
        if wm:
            src = src.replace(MW.TAIL, MW.emit(wm, LAYER) + '\n' + MW.TAIL)
        if not args.no_backup:
            shutil.copy2(args.pcb, args.pcb + '.bak')
        open(args.pcb, 'w').write(src)
        print(f'restored {n} text items and {len(wm)} wordmark polygons')
        return 0

    out = compute(src, grow_mm=args.grow, res=args.res)

    if args.preview:
        m = out['result']
        img = np.zeros(m.shape + (3,), np.uint8)
        img[..., :] = (16, 18, 22)
        img[m] = (238, 238, 238)
        im = Image.fromarray(img).transpose(Image.FLIP_LEFT_RIGHT)
        im.thumbnail((3000, 3000))
        im.save(args.preview)
        print(f'  preview -> {args.preview}')

    if not args.apply:
        return 0

    # suppress the consumed text first, then swap in the boolean result
    src2 = src
    records = []
    for t in out['touching']:
        if not t['uuid']:
            continue
        src2, res = suppress(src2, t['uuid'])
        if res:
            how, block = res
            records.append(dict(uuid=t['uuid'], how=how, block=block, text=t['text']))
    src2, removed = MW.strip(src2)
    src2 = src2.replace(MW.TAIL, MW.emit(out['rings'], LAYER) + '\n' + MW.TAIL)
    json.dump(dict(suppressed=records, wordmark=out['wm']), open(STATE, 'w'), indent=1)
    if not args.no_backup:
        shutil.copy2(args.pcb, args.pcb + '.bak')
    open(args.pcb, 'w').write(src2)
    nhide = sum(1 for r in records if r['how'] == 'hide')
    ncut = sum(1 for r in records if r['how'] == 'cut')
    print(f'  replaced {removed} wordmark polys with {len(out["rings"])}; '
          f'hid {nhide} designators, cut {ncut} gr_text')
    return 0


if __name__ == '__main__':
    sys.exit(main())
