#!/usr/bin/env python3
"""Thermal plate FDM for twin28xx: copper I^2R map -> steady-state temperature rise.

Usage: thermal_solve.py <copper.json> <powersim_dir> <outdir>
"""
import json
import math
import pickle
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path
from scipy import sparse
from scipy.sparse.linalg import spsolve

PITCH_E = 0.25e-3
PITCH_T = 0.5e-3
T_LAYER = {'F.Cu': 35e-6, 'In1.Cu': 15.2e-6, 'In2.Cu': 15.2e-6, 'B.Cu': 35e-6}
LAYERS = ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu']
RHO_CU = 1.72e-8 * (1 + 0.00393 * (45 - 20))
K_CU = 385.0
K_FR4 = 0.5
T_BOARD = 1.6167e-3
H_FACE = 12.0          # W/m^2K per face
AMBIENT = 25.0

I_REF = 5.0            # A per driver used in electrical solve
DT_LIMITS = [10.0, 20.0, 30.0, 40.0]

# device heat (added separately, scenario-independent placement)
FET_XY = (116.4, 107.7)
DRV_XY = {'U14': (135.5, 110.3), 'U15': (92.3, 110.3)}
R_FET = 0.004


def main():
    d = json.load(open(sys.argv[1]))
    simdir = sys.argv[2]
    outdir = sys.argv[3]
    with open(f'{simdir}/results.pkl', 'rb') as f:
        saved = pickle.load(f)
    x0, y0, nxe, nye = saved['grid']

    # thermal grid
    bx0, by0, bx1, by1 = d['outline_bbox']
    nx = int(math.ceil((bx1 - bx0) / 0.5)) + 1
    ny = int(math.ceil((by1 - by0) / 0.5)) + 1

    # copper coverage per layer at thermal resolution
    gx = bx0 + np.arange(nx) * 0.5
    gy = by0 + np.arange(ny) * 0.5
    cov = {l: np.zeros((ny, nx)) for l in LAYERS}
    for z in d['copper_all']:
        if z['layer'] not in LAYERS:
            continue
        pts = np.array(z['pts'])
        ix0 = max(0, int((pts[:, 0].min() - bx0) / 0.5) - 1)
        ix1 = min(nx - 1, int((pts[:, 0].max() - bx0) / 0.5) + 1)
        iy0 = max(0, int((pts[:, 1].min() - by0) / 0.5) - 1)
        iy1 = min(ny - 1, int((pts[:, 1].max() - by0) / 0.5) + 1)
        if ix1 < ix0 or iy1 < iy0:
            continue
        X, Y = np.meshgrid(gx[ix0:ix1 + 1], gy[iy0:iy1 + 1])
        inside = Path(pts).contains_points(
            np.column_stack([X.ravel(), Y.ravel()])).reshape(X.shape)
        cov[z['layer']][iy0:iy1 + 1, ix0:ix1 + 1] = np.maximum(
            cov[z['layer']][iy0:iy1 + 1, ix0:ix1 + 1], inside.astype(float))

    kt = sum(K_CU * T_LAYER[l] * cov[l] for l in LAYERS) + K_FR4 * T_BOARD
    print(f'k*t range: {kt.min()*1e3:.2f} .. {kt.max()*1e3:.2f} mW/K per square')

    # assemble conduction matrix
    N = nx * ny

    def iid(iy, ix):
        return iy * nx + ix

    rows, cols, vals = [], [], []
    diag = np.zeros(N)
    for iy in range(ny):
        for ix in range(nx):
            for dy, dx in ((0, 1), (1, 0)):
                iy2, ix2 = iy + dy, ix + dx
                if iy2 >= ny or ix2 >= nx:
                    continue
                g = 2.0 / (1.0 / kt[iy, ix] + 1.0 / kt[iy2, ix2])
                a, b = iid(iy, ix), iid(iy2, ix2)
                rows.extend([a, b]); cols.extend([b, a]); vals.extend([-g, -g])
                diag[a] += g; diag[b] += g
    diag += 2 * H_FACE * PITCH_T * PITCH_T  # both faces
    rows.extend(range(N)); cols.extend(range(N)); vals.extend(diag)
    K = sparse.coo_matrix((vals, (rows, cols)), shape=(N, N)).tocsr()

    # heat maps per scenario from electrical p_cells (at I_REF per driver)
    results = {}
    for feed, r in saved['results'].items():
        Q = np.zeros((ny, nx))
        for (net, layer, iye, ixe), p in r['p_cells'].items():
            X = x0 + ixe * 0.25
            Y = y0 + iye * 0.25
            ix = min(nx - 1, max(0, int(round((X - bx0) / 0.5))))
            iy = min(ny - 1, max(0, int(round((Y - by0) / 0.5))))
            Q[iy, ix] += p
        # FET conduction heat (carries 2*I_REF), spread over DFN5x6 footprint
        Q_fet = (2 * I_REF) ** 2 * R_FET
        Qc = Q.copy()
        fcells = []
        for iy in range(ny):
            for ix in range(nx):
                if abs(gx[ix] - FET_XY[0]) <= 2.5 and abs(gy[iy] - FET_XY[1]) <= 2.0:
                    fcells.append((iy, ix))
        for iy, ix in fcells:
            Qc[iy, ix] += Q_fet / len(fcells)

        T = spsolve(K, Qc.ravel() * 1.0).reshape(ny, nx)
        results[feed] = {'Q': Qc, 'T': T, 'p_copper': r['p_copper_total'],
                         'drops': r['drops']}
        print(f"{feed}: P_cu={r['p_copper_total']:.3f}W  P_fet={Q_fet:.2f}W  "
              f"dT_max={T.max():.2f}K @{I_REF}A/driver")
        for dt in DT_LIMITS:
            iscale = I_REF * math.sqrt(dt / T.max())
            print(f"   dT<={dt:.0f}K  -> I_bus per driver {iscale:.1f}A "
                  f"(total {2*iscale:.1f}A)")

    # current-density maps (A/mm^2) from per-cell power
    for feed, r in saved['results'].items():
        Jmax = 0; where = None
        Jmap = {l: np.zeros((nye, nxe)) for l in LAYERS}
        for (net, layer, iye, ixe), p in r['p_cells'].items():
            q = p / (PITCH_E ** 2)                      # W/m^2
            t = T_LAYER[layer]
            Jsheet = math.sqrt(max(q, 0) * t / RHO_CU)  # A/m width
            J = Jsheet / t / 1e6                        # A/mm^2
            Jmap[layer][iye, ixe] = max(Jmap[layer][iye, ixe], J)
            if J > Jmax:
                Jmax, where = J, (net, layer, x0 + ixe * 0.25, y0 + iye * 0.25)
        results[feed]['Jmax'] = (Jmax, where)
        print(f"{feed}: Jmax={Jmax:.1f} A/mm^2 at {where} @{I_REF}A/driver")
        results[feed]['Jmap'] = Jmap

    # plots
    for feed in results:
        T = results[feed]['T']
        fig, ax = plt.subplots(figsize=(10, 5))
        im = ax.imshow(T, origin='upper', cmap='inferno',
                       extent=[bx0, bx1, by1, by0])
        fig.colorbar(im, label=f'dT (K) @ {I_REF}A/driver')
        ax.set_title(f'twin28xx board temperature rise — feed {feed}, '
                     f'{I_REF}A bus per driver (copper+FET heat only)')
        for (X, Y), lbl in [((135.5, 110.3), 'U14'), ((92.3, 110.3), 'U15'),
                            ((116.4, 107.7), 'U4'), ((152.2, 115), 'J6'),
                            ((77.8, 115), 'J4')]:
            ax.plot(X, Y, 'w+'); ax.text(X + 0.6, Y, lbl, color='w', fontsize=7)
        fig.tight_layout()
        fig.savefig(f'{outdir}/thermal_{feed}.png', dpi=140)
        plt.close(fig)

        Jall = np.maximum.reduce([results[feed]['Jmap'][l] for l in LAYERS])
        fig, ax = plt.subplots(figsize=(10, 5))
        im = ax.imshow(Jall, origin='upper', cmap='viridis',
                       extent=[x0, x0 + nxe * 0.25, y0 + nye * 0.25, y0])
        fig.colorbar(im, label='J (A/mm2), max across layers')
        ax.set_title(f'current density — feed {feed} @ {I_REF}A/driver')
        fig.tight_layout()
        fig.savefig(f'{outdir}/current_density_{feed}.png', dpi=140)
        plt.close(fig)

    with open(f'{outdir}/thermal_results.pkl', 'wb') as f:
        pickle.dump({k: {'T': v['T'], 'p_copper': v['p_copper'],
                         'Jmax': v['Jmax']} for k, v in results.items()}, f)
    print('done')


if __name__ == '__main__':
    main()
