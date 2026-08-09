"""Marching-squares contour tracing of a binary mask -> closed polygons."""
import numpy as np

# For code = TL | TR<<1 | BR<<2 | BL<<3, the directed edge crossings that keep
# filled pixels on the left. Edges: T(op) B(ottom) L(eft) R(ight) of the cell.
_TABLE = {
    1:  [('L', 'T')],
    2:  [('T', 'R')],
    3:  [('L', 'R')],
    4:  [('R', 'B')],
    5:  [('L', 'T'), ('R', 'B')],       # saddle, resolved consistently
    6:  [('T', 'B')],
    7:  [('L', 'B')],
    8:  [('B', 'L')],
    9:  [('B', 'T')],
    10: [('T', 'R'), ('B', 'L')],       # saddle
    11: [('B', 'R')],
    12: [('R', 'L')],
    13: [('R', 'T')],
    14: [('T', 'L')],
}


def _edge_key(r, c, side):
    """Identify a cell edge by the shared lattice edge, so neighbours agree."""
    if side == 'T':
        return (r, c, 'h')
    if side == 'B':
        return (r + 1, c, 'h')
    if side == 'L':
        return (r, c, 'v')
    return (r, c + 1, 'v')


def _edge_point(key):
    """Midpoint of the lattice edge, in the *unpadded* mask's pixel-centre frame.

    The mask is padded by one pixel before tracing, so undo that here. Midpoints
    land exactly on the half-pixel area boundary between filled and empty.
    """
    r, c, o = key
    return (c - 0.5, r - 1.0) if o == 'h' else (c - 1.0, r - 0.5)


def contours(mask):
    """mask: 2D bool. -> list of closed rings, each a list of (x, y) in pixel units.

    Rings are oriented so filled area is on the left; outer rings and holes come
    back with opposite winding.
    """
    m = np.pad(mask, 1, constant_values=False).astype(np.uint8)
    tl = m[:-1, :-1]
    tr = m[:-1, 1:]
    br = m[1:, 1:]
    bl = m[1:, :-1]
    code = tl | (tr << 1) | (br << 2) | (bl << 3)
    rs, cs = np.nonzero((code > 0) & (code < 15))

    nxt = {}
    for r, c in zip(rs.tolist(), cs.tolist()):
        for a, b in _TABLE[int(code[r, c])]:
            nxt[_edge_key(r, c, a)] = _edge_key(r, c, b)

    rings = []
    while nxt:
        start = next(iter(nxt))
        ring = []
        k = start
        while True:
            nk = nxt.pop(k, None)
            ring.append(_edge_point(k))
            if nk is None:
                break
            k = nk
            if k == start:
                break
        if len(ring) >= 3:
            rings.append(ring)
    return rings


def signed_area(ring):
    a = 0.0
    for i in range(len(ring)):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % len(ring)]
        a += x0 * y1 - x1 * y0
    return a / 2.0
