#!/usr/bin/env python3
"""twin28xx battery-bus current/thermal FDM simulation.

Electrical: rasterize +BATT / VCC / GND copper (zones+segments+pads+vias) per
layer, build a nodal conductance network, inject battery current at J6/J4,
draw load at each DRV8316 (VM pins -> GND pins/EP), solve node voltages.

Thermal: 2D plate model of the whole board, k_eff from total copper coverage,
convection+radiation from both faces, heated by the copper I^2R map (and
optionally driver package losses).

Scenarios: feed right (J6), feed left (J4), feed both.
"""
import json
import math
import sys

import numpy as np
from matplotlib.path import Path
from scipy import sparse
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import spsolve

# ---------------- parameters ----------------
PITCH = 0.25          # mm, electrical grid
TPITCH = 0.5          # mm, thermal grid
RHO_CU = 1.72e-8 * (1 + 0.00393 * (45 - 20))   # ohm*m @ 45C copper
T_LAYER = {'F.Cu': 35e-6, 'In1.Cu': 15.2e-6, 'In2.Cu': 15.2e-6, 'B.Cu': 35e-6}
LAYERS = ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu']
Z_LAYER = {'F.Cu': 0.0175, 'In1.Cu': 0.253, 'In2.Cu': 1.334, 'B.Cu': 1.599}  # mm midplanes
VIA_PLATE = 20e-6     # m, via barrel plating
R_FET = 0.004         # ohm, U4 WSD4066DN RDS(on) assumption
R_LEAD = 0.002        # ohm per battery lead per connector (both-sides split)
H_CONV = 12.0         # W/m^2K per face (natural convection + radiation)
K_CU = 385.0
K_FR4_T = 0.5         # W/mK in-plane dielectric
T_BOARD = 1.6167e-3   # m

I_PER_DRIVER = 5.0    # A bus current per driver for reported operating point

NET_SUPPLY = ('+BATT', 'VCC')
NET_RETURN = ('GND',)
ALL_NETS = ('+BATT', 'VCC', 'GND')

# component-pad groupings (merged supernodes)
GROUPS = {
    'U14.VM':  [('U14', p) for p in ('9', '10', '11')],
    'U14.GND': [('U14', p) for p in ('2', '4', '12', '15', '18', '26', '41')],
    'U15.VM':  [('U15', p) for p in ('9', '10', '11')],
    'U15.GND': [('U15', p) for p in ('2', '4', '12', '15', '18', '26', '41')],
    'U4.IN':   [('U4', p) for p in ('1', '3')],
    'U4.OUT':  [('U4', p) for p in ('5', '6', '7', '8', '9', '10')],
    'J6.P':    [('J6', '2')], 'J6.G': [('J6', '1')],
    'J4.P':    [('J4', '2')], 'J4.G': [('J4', '1')],
}


def load(path):
    return json.load(open(path))


def build_grid(bbox):
    x0, y0, x1, y1 = bbox
    nx = int(math.ceil((x1 - x0) / PITCH)) + 1
    ny = int(math.ceil((y1 - y0) / PITCH)) + 1
    return x0, y0, nx, ny


def raster(d, x0, y0, nx, ny):
    """masks[(net, layer)] = bool[ny, nx]; padcells[(ref,pad)] = [(net,layer,iy,ix)]"""
    gx = x0 + np.arange(nx) * PITCH
    gy = y0 + np.arange(ny) * PITCH
    masks = {(n, l): np.zeros((ny, nx), bool) for n in ALL_NETS for l in LAYERS}
    padcells = {}

    def sub(bx0, by0, bx1, by1, pad=0.3):
        ix0 = max(0, int((bx0 - pad - x0) / PITCH))
        ix1 = min(nx - 1, int(math.ceil((bx1 + pad - x0) / PITCH)))
        iy0 = max(0, int((by0 - pad - y0) / PITCH))
        iy1 = min(ny - 1, int(math.ceil((by1 + pad - y0) / PITCH)))
        return ix0, ix1, iy0, iy1

    # zones
    for z in d['zones']:
        if z['net'] not in ALL_NETS or z['layer'] not in LAYERS:
            continue
        pts = np.array(z['pts'])
        ix0, ix1, iy0, iy1 = sub(pts[:, 0].min(), pts[:, 1].min(),
                                 pts[:, 0].max(), pts[:, 1].max(), 0)
        if ix1 < ix0 or iy1 < iy0:
            continue
        X, Y = np.meshgrid(gx[ix0:ix1 + 1], gy[iy0:iy1 + 1])
        inside = Path(pts).contains_points(
            np.column_stack([X.ravel(), Y.ravel()])).reshape(X.shape)
        m = masks[(z['net'], z['layer'])]
        m[iy0:iy1 + 1, ix0:ix1 + 1] |= inside

    # segments
    for s in d['segments']:
        if s['net'] not in ALL_NETS or s['layer'] not in LAYERS:
            continue
        r = s['w'] / 2
        ix0, ix1, iy0, iy1 = sub(min(s['x1'], s['x2']) - r, min(s['y1'], s['y2']) - r,
                                 max(s['x1'], s['x2']) + r, max(s['y1'], s['y2']) + r)
        X, Y = np.meshgrid(gx[ix0:ix1 + 1], gy[iy0:iy1 + 1])
        dx, dy = s['x2'] - s['x1'], s['y2'] - s['y1']
        L2 = dx * dx + dy * dy
        if L2 == 0:
            t = np.zeros_like(X)
        else:
            t = np.clip(((X - s['x1']) * dx + (Y - s['y1']) * dy) / L2, 0, 1)
        dist = np.hypot(X - (s['x1'] + t * dx), Y - (s['y1'] + t * dy))
        m = masks[(s['net'], s['layer'])]
        m[iy0:iy1 + 1, ix0:ix1 + 1] |= dist <= max(r, PITCH * 0.5)

    def mark_disc(net, layers, cx, cy, radius, key=None):
        ix0, ix1, iy0, iy1 = sub(cx - radius, cy - radius, cx + radius, cy + radius)
        X, Y = np.meshgrid(gx[ix0:ix1 + 1], gy[iy0:iy1 + 1])
        inside = np.hypot(X - cx, Y - cy) <= max(radius, PITCH * 0.6)
        for l in layers:
            masks[(net, l)][iy0:iy1 + 1, ix0:ix1 + 1] |= inside
            if key is not None:
                for yy, xx in zip(*np.nonzero(inside)):
                    padcells.setdefault(key, []).append((net, l, iy0 + yy, ix0 + xx))

    def mark_rect(net, layers, cx, cy, w, h, ang, key):
        rad = math.hypot(w, h) / 2
        ix0, ix1, iy0, iy1 = sub(cx - rad, cy - rad, cx + rad, cy + rad)
        X, Y = np.meshgrid(gx[ix0:ix1 + 1], gy[iy0:iy1 + 1])
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        # rotate world into pad frame (y-down convention consistent w/ extract)
        Xl = (X - cx) * ca - (Y - cy) * sa
        Yl = (X - cx) * sa + (Y - cy) * ca
        inside = (np.abs(Xl) <= max(w / 2, PITCH * 0.55)) & \
                 (np.abs(Yl) <= max(h / 2, PITCH * 0.55))
        for l in layers:
            masks[(net, l)][iy0:iy1 + 1, ix0:ix1 + 1] |= inside
            if key is not None:
                for yy, xx in zip(*np.nonzero(inside)):
                    padcells.setdefault(key, []).append((net, l, iy0 + yy, ix0 + xx))

    # pads
    tht_barrels = []
    for p in d['pads']:
        if p['net'] not in ALL_NETS:
            continue
        layers = LAYERS if p['tht'] or '*.Cu' in p['layers'] else \
            [l for l in p['layers'] if l in LAYERS]
        key = (p['ref'], p['pad'])
        if p['shape'] == 'circle':
            mark_disc(p['net'], layers, p['x'], p['y'], p['w'] / 2, key)
        else:
            mark_rect(p['net'], layers, p['x'], p['y'], p['w'], p['h'], p['angle'], key)
        if p['tht']:
            tht_barrels.append({'net': p['net'], 'x': p['x'], 'y': p['y'],
                                'drill': max(p['w'], p['h']) * 0.7})
    # NOTE: vias are handled as vertical links only (build_network); painting
    # their annuli onto all layers would fabricate copper on layers the net
    # doesn't occupy (e.g. VCC islands inside the In1 GND plane).
    return masks, padcells, tht_barrels


class DSU:
    def __init__(self):
        self.p = {}

    def find(self, a):
        while self.p.setdefault(a, a) != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def build_network(d, masks, padcells, tht_barrels, x0, y0, nx, ny):
    """Return (G_coo lists, node index map, named nodes)."""
    dsu = DSU()
    # base node id = (net, layer, iy, ix)
    # merge component pads into supernodes
    named = {}
    for gname, pads in GROUPS.items():
        cells = []
        for key in pads:
            cells += padcells.get(key, [])
        if not cells:
            continue
        first = cells[0]
        for c in cells[1:]:
            dsu.union(c, first)
        named[gname] = first
    # merge remaining multi-cell pads (each pad is one metal blob)
    grouped = {k for pads in GROUPS.values() for k in pads}
    for key, cells in padcells.items():
        if key in grouped or len(cells) < 2:
            continue
        for c in cells[1:]:
            dsu.union(c, cells[0])

    edges = []   # (nodeA, nodeB, conductance)

    # in-plane FDM edges
    for (net, layer), m in masks.items():
        g_sheet = T_LAYER[layer] / RHO_CU   # S per square
        ys, xs = np.nonzero(m)
        cellset = m
        for dy_, dx_ in ((0, 1), (1, 0)):
            y2, x2 = ys + dy_, xs + dx_
            ok = (y2 < ny) & (x2 < nx)
            ok[ok] &= cellset[y2[ok], x2[ok]]
            for yy, xx, yy2, xx2 in zip(ys[ok], xs[ok], y2[ok], x2[ok]):
                edges.append(((net, layer, yy, xx), (net, layer, yy2, xx2), g_sheet))

    # via + THT barrel vertical edges: attach to nearest real copper cell per
    # layer (within ~annulus reach); chain consecutive attached layers.
    def vlink(net, x, y, drill_mm, reach_mm=0.5, layers=LAYERS):
        ix = int(round((x - x0) / PITCH))
        iy = int(round((y - y0) / PITCH))
        r = max(1, int(round(reach_mm / PITCH)))
        attach = []
        for l in layers:
            m = masks[(net, l)]
            best = None
            for dy_ in range(-r, r + 1):
                for dx_ in range(-r, r + 1):
                    yy, xx = iy + dy_, ix + dx_
                    if 0 <= yy < ny and 0 <= xx < nx and m[yy, xx]:
                        d2 = dy_ * dy_ + dx_ * dx_
                        if best is None or d2 < best[0]:
                            best = (d2, yy, xx)
            if best is not None:
                attach.append((l, best[1], best[2]))
        area = math.pi * drill_mm * 1e-3 * VIA_PLATE  # m^2 barrel cross-section
        for (la, ya, xa), (lb, yb, xb) in zip(attach[:-1], attach[1:]):
            span = max(abs(Z_LAYER[lb] - Z_LAYER[la]), 0.1) * 1e-3
            R = RHO_CU * span / area
            edges.append(((net, la, ya, xa), (net, lb, yb, xb), 1.0 / R))

    for v in d['vias']:
        if v['net'] in ALL_NETS:
            vlink(v['net'], v['x'], v['y'], v['drill'])
    for b in tht_barrels:
        vlink(b['net'], b['x'], b['y'], b['drill'])

    return dsu, edges, named


def solve_scenario(dsu, edges, named, feed, i_per_driver):
    """feed in {'right','left','both'}; returns dict of results + node voltages."""
    # external elements
    ext = [('U4.IN', 'U4.OUT', 1.0 / R_FET)]
    inj = {}   # node -> A
    bp, bm = ('B+',), ('B-',)
    conns = {'right': ['J6'], 'left': ['J4'], 'both': ['J6', 'J4']}[feed]
    for j in conns:
        ext.append(('B+', f'{j}.P', 1.0 / R_LEAD))
        ext.append(('B-', f'{j}.G', 1.0 / R_LEAD))
    itot = 2 * i_per_driver
    inj['B+'] = itot
    inj['B-'] = -itot
    for drv in ('U14', 'U15'):
        inj[f'{drv}.VM'] = inj.get(f'{drv}.VM', 0) - i_per_driver
        inj[f'{drv}.GND'] = inj.get(f'{drv}.GND', 0) + i_per_driver

    # canonical node ids
    def canon(n):
        if isinstance(n, str):
            if n in named:
                return dsu.find(named[n])
            return n  # B+/B-
        return dsu.find(n)

    idx = {}

    def nid(n):
        c = canon(n)
        if c not in idx:
            idx[c] = len(idx)
        return idx[c]

    rows, cols, vals = [], [], []

    def add_edge(a, b, g):
        ia, ib = nid(a), nid(b)
        if ia == ib:
            return
        rows.extend([ia, ib, ia, ib])
        cols.extend([ia, ib, ib, ia])
        vals.extend([g, g, -g, -g])

    for a, b, g in edges:
        add_edge(a, b, g)
    for a, b, g in ext:
        add_edge(a, b, g)

    n = len(idx)
    G = sparse.coo_matrix((vals, (rows, cols)), shape=(n, n)).tocsr()
    I = np.zeros(n)
    for node, amps in inj.items():
        I[nid(node)] += amps

    # handle disconnected components: solve only those carrying injection
    ncomp, labels = connected_components(G != 0, directed=False)
    V = np.full(n, np.nan)
    for c in range(ncomp):
        sel = labels == c
        Isub = I[sel]
        if abs(Isub).sum() < 1e-12:
            continue
        if abs(Isub.sum()) > 1e-9:
            raise RuntimeError(f'component {c}: unbalanced injection {Isub.sum()}')
        Gsub = G[sel][:, sel].tolil()
        ref = 0
        Gsub[ref, :] = 0
        Gsub[ref, ref] = 1.0
        Isub = Isub.copy()
        Isub[ref] = 0.0
        Vsub = spsolve(Gsub.tocsr(), Isub)
        V[sel] = Vsub

    def volt(node):
        return V[idx[canon(node)]] if canon(node) in idx else np.nan

    res = {
        'feed': feed,
        'i_per_driver': i_per_driver,
        'V': V, 'idx': idx, 'canon': canon, 'labels': labels,
        'drops': {
            'supply_J_to_U4in': {j: volt(f'{j}.P') - volt('U4.IN') for j in conns},
            'U4_fet': volt('U4.IN') - volt('U4.OUT'),
            'vcc_U4_to_U14VM': volt('U4.OUT') - volt('U14.VM'),
            'vcc_U4_to_U15VM': volt('U4.OUT') - volt('U15.VM'),
            'gnd_U14_to_J': {j: volt('U14.GND') - volt(f'{j}.G') for j in conns},
            'gnd_U15_to_J': {j: volt('U15.GND') - volt(f'{j}.G') for j in conns},
            'total_loop_U14': (volt('B+') - volt('U14.VM')) + (volt('U14.GND') - volt('B-')),
            'total_loop_U15': (volt('B+') - volt('U15.VM')) + (volt('U15.GND') - volt('B-')),
        },
    }
    return res


def edge_power(edges, res, exclude_named=True):
    """per-cell dissipation dict cell->W and total; edge list in copper only."""
    V, idx, canon = res['V'], res['idx'], res['canon']
    pw = {}
    total = 0.0
    for a, b, g in edges:
        ia, ib = idx.get(canon(a)), idx.get(canon(b))
        if ia is None or ib is None or ia == ib:
            continue
        dv = V[ia] - V[ib]
        if not np.isfinite(dv):
            continue
        p = g * dv * dv
        total += p
        for node in (a, b):
            if not isinstance(node, str):
                pw[node] = pw.get(node, 0.0) + p / 2
    return pw, total


def main():
    d = load(sys.argv[1])
    outdir = sys.argv[2]
    x0, y0, nx, ny = build_grid(d['outline_bbox'])
    print(f'grid {nx}x{ny} @ {PITCH}mm')
    masks, padcells, tht = raster(d, x0, y0, nx, ny)
    for k, m in masks.items():
        if m.any():
            print(k, int(m.sum()), 'cells')
    dsu, edges, named = build_network(d, masks, padcells, tht, x0, y0, nx, ny)
    print('named nodes:', sorted(named))
    print('edges:', len(edges))

    results = {}
    for feed in ('right', 'left', 'both'):
        res = solve_scenario(dsu, edges, named, feed, I_PER_DRIVER)
        pw, ptot = edge_power(edges, res)
        res['p_copper_total'] = ptot
        res['p_cells'] = pw
        results[feed] = res
        dr = res['drops']
        print(f"\n=== feed {feed} @ {I_PER_DRIVER}A/driver ===")
        for k, v in dr.items():
            if isinstance(v, dict):
                print(f"  {k}: " + ', '.join(f'{j}={1e3*x:.2f}mV' for j, x in v.items()))
            else:
                print(f"  {k}: {1e3*v:.2f}mV")
        print(f"  copper dissipation: {ptot:.3f} W")
        r14 = res['drops']['total_loop_U14'] / I_PER_DRIVER
        r15 = res['drops']['total_loop_U15'] / I_PER_DRIVER
        print(f"  R_loop board (U14): {1e3*r14:.2f} mOhm   (U15): {1e3*r15:.2f} mOhm")

    np.save(f'{outdir}/masks.npy', {str(k): v for k, v in masks.items()}, allow_pickle=True)
    import pickle
    with open(f'{outdir}/results.pkl', 'wb') as f:
        pickle.dump({'results': {k: {kk: vv for kk, vv in r.items()
                                     if kk in ('feed', 'drops', 'p_copper_total', 'p_cells')}
                                 for k, r in results.items()},
                     'grid': (x0, y0, nx, ny)}, f)
    print('\nsaved results')


if __name__ == '__main__':
    main()
