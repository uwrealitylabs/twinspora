#!/usr/bin/env python3
"""Extract copper geometry for selected nets from a KiCad 10.99 .kicad_pcb.

Outputs JSON: zones (filled polygons per layer), segments, vias, pads (global
coords), board outline bbox, and locations of key footprints.

Usage: python3 extract_copper.py <board.kicad_pcb> <out.json> NET1 NET2 ...
"""
import json
import math
import sys


def tokenize(text):
    toks = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in "()":
            toks.append(c)
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while j < n:
                if text[j] == '\\' and j + 1 < n:
                    buf.append(text[j + 1])
                    j += 2
                elif text[j] == '"':
                    break
                else:
                    buf.append(text[j])
                    j += 1
            toks.append(('str', ''.join(buf)))
            i = j + 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in '()"':
                j += 1
            toks.append(('atom', text[i:j]))
            i = j
    return toks


def parse(toks):
    it = iter(toks)

    def build():
        out = []
        for t in it:
            if t == '(':
                out.append(build())
            elif t == ')':
                return out
            else:
                out.append(t)
        return out

    root = None
    for t in it:
        if t == '(':
            root = build()
            break
    return root


def atom(x):
    if isinstance(x, tuple):
        return x[1]
    return x


def num(x):
    return float(atom(x))


def find_all(node, key):
    for item in node:
        if isinstance(item, list) and item and atom(item[0]) == key:
            yield item


def find_one(node, key, default=None):
    for item in find_all(node, key):
        return item
    return default


def get_net(node):
    n = find_one(node, 'net')
    if n is None:
        return None
    return atom(n[1])


def get_layers(node):
    l = find_one(node, 'layers')
    if l is None:
        l = find_one(node, 'layer')
    if l is None:
        return []
    return [atom(x) for x in l[1:]]


def rotate_pt(x, y, deg):
    """Rotate local footprint coords into global. KiCad y-down; positive angle = CCW on screen."""
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    # y-down + CCW-on-screen => in raw coords rotate by -deg in standard convention
    return (x * c + y * s, -x * s + y * c)


def main():
    board_path, out_path, *nets = sys.argv[1:]
    nets = set(nets)
    text = open(board_path).read()
    tree = parse(tokenize(text))

    out = {
        'nets': sorted(nets),
        'zones': [],      # {net, layer, pts: [[x,y],...]}
        'segments': [],   # {net, layer, x1,y1,x2,y2,w}
        'vias': [],       # {net, x, y, size, drill, layers}
        'pads': [],       # {ref, pad, net, x, y, w, h, shape, angle, layers, tht}
        'outline_bbox': None,
        'copper_all': [], # coverage polygons for ALL nets (for thermal k_eff): {layer, pts} zones only
        'footprints': {}, # ref -> {x, y, angle, value}
    }

    xs, ys = [], []
    for item in tree:
        if not isinstance(item, list):
            continue
        kind = atom(item[0]) if item else None

        if kind in ('gr_line', 'gr_arc', 'gr_rect', 'gr_circle', 'gr_curve', 'gr_poly'):
            lay = get_layers(item)
            if 'Edge.Cuts' in lay:
                for k in ('start', 'end', 'center', 'mid'):
                    p = find_one(item, k)
                    if p:
                        xs.append(num(p[1])); ys.append(num(p[2]))
                pts = find_one(item, 'pts')
                if pts:
                    for xy in find_all(pts, 'xy'):
                        xs.append(num(xy[1])); ys.append(num(xy[2]))

        elif kind == 'segment':
            net = get_net(item)
            if net in nets:
                s, e = find_one(item, 'start'), find_one(item, 'end')
                w = find_one(item, 'width')
                lay = get_layers(item)
                out['segments'].append({
                    'net': net, 'layer': lay[0] if lay else None,
                    'x1': num(s[1]), 'y1': num(s[2]),
                    'x2': num(e[1]), 'y2': num(e[2]), 'w': num(w[1])})

        elif kind == 'via':
            net = get_net(item)
            if net in nets:
                at = find_one(item, 'at')
                size = find_one(item, 'size')
                drill = find_one(item, 'drill')
                out['vias'].append({
                    'net': net, 'x': num(at[1]), 'y': num(at[2]),
                    'size': num(size[1]), 'drill': num(drill[1]),
                    'layers': get_layers(item)})

        elif kind == 'zone':
            znet_node = find_one(item, 'net_name')
            znet = atom(znet_node[1]) if znet_node else get_net(item)
            for fp in find_all(item, 'filled_polygon'):
                lay = find_one(fp, 'layer')
                layer = atom(lay[1]) if lay else None
                pts_node = find_one(fp, 'pts')
                pts = [[num(xy[1]), num(xy[2])] for xy in find_all(pts_node, 'xy')]
                if len(pts) >= 3:
                    rec = {'net': znet, 'layer': layer, 'pts': pts}
                    if znet in nets:
                        out['zones'].append(rec)
                    if layer in ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'):
                        out['copper_all'].append({'layer': layer, 'pts': pts, 'net': znet})

        elif kind == 'footprint':
            at = find_one(item, 'at')
            if at is not None:
                fx, fy = num(at[1]), num(at[2])
                fang = num(at[3]) if len(at) > 3 and not isinstance(at[3], list) else 0.0
                fsx, fsy = 1.0, 1.0
            else:
                # KiCad 10.99 fork format: (transform (translate x y) (rotate deg) (scale sx sy))
                tr = find_one(item, 'transform')
                if tr is None:
                    continue
                tl = find_one(tr, 'translate')
                ro = find_one(tr, 'rotate')
                sc = find_one(tr, 'scale')
                fx, fy = num(tl[1]), num(tl[2])
                fang = num(ro[1]) if ro is not None else 0.0
                fsx = num(sc[1]) if sc is not None else 1.0
                fsy = num(sc[2]) if sc is not None else 1.0
            ref = None
            value = None
            for prop in find_all(item, 'property'):
                pname = atom(prop[1])
                if pname == 'Reference':
                    ref = atom(prop[2])
                elif pname == 'Value':
                    value = atom(prop[2])
            out['footprints'][ref] = {'x': fx, 'y': fy, 'angle': fang, 'value': value}
            for pad in find_all(item, 'pad'):
                pnet = get_net(pad)
                if pnet not in nets:
                    continue
                pname = atom(pad[1])
                ptype = atom(pad[2])   # smd | thru_hole | np_thru_hole | connect
                pshape = atom(pad[3])
                pat = find_one(pad, 'at')
                px, py = num(pat[1]), num(pat[2])
                pang = num(pat[3]) if len(pat) > 3 and not isinstance(pat[3], list) else 0.0
                psize = find_one(pad, 'size')
                w, h = num(psize[1]), num(psize[2])
                gx_off, gy_off = rotate_pt(px * fsx, py * fsy, fang)
                gx, gy = fx + gx_off, fy + gy_off
                lay = get_layers(pad)
                out['pads'].append({
                    'ref': ref, 'pad': pname, 'net': pnet,
                    'x': gx, 'y': gy, 'w': w, 'h': h, 'shape': pshape,
                    'angle': pang, 'layers': lay,
                    'tht': ptype == 'thru_hole'})

    if xs:
        out['outline_bbox'] = [min(xs), min(ys), max(xs), max(ys)]

    json.dump(out, open(out_path, 'w'))
    print(f"bbox={out['outline_bbox']}")
    print(f"zones={len(out['zones'])} segs={len(out['segments'])} vias={len(out['vias'])} pads={len(out['pads'])} copper_all={len(out['copper_all'])}")


if __name__ == '__main__':
    main()
