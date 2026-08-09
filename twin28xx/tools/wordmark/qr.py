"""Minimal QR Code encoder/decoder (byte mode) for regenerating the board's QR.

Only what this board needs: byte mode, versions 1-10, all four ECC levels.
The decoder exists so the encoder can be checked against the QR already on the
board rather than trusted blind.
"""

# (ec codewords per block, [(block count, data codewords per block), ...]) by
# version 1-10 and level. Total codewords = sum(count*(data+ec)).
RS_TABLE = {
    #        L                      M                      Q                      H
    1:  ((7, [(1, 19)]),   (10, [(1, 16)]),   (13, [(1, 13)]),   (17, [(1, 9)])),
    2:  ((10, [(1, 34)]),  (16, [(1, 28)]),   (22, [(1, 22)]),   (28, [(1, 16)])),
    3:  ((15, [(1, 55)]),  (26, [(1, 44)]),   (18, [(2, 17)]),   (22, [(2, 13)])),
    4:  ((20, [(1, 80)]),  (18, [(2, 32)]),   (26, [(2, 24)]),   (16, [(4, 9)])),
    5:  ((26, [(1, 108)]), (24, [(2, 43)]),   (18, [(2, 15), (2, 16)]),
         (22, [(2, 11), (2, 12)])),
    6:  ((18, [(2, 68)]),  (16, [(4, 27)]),   (24, [(4, 19)]),   (28, [(4, 15)])),
    7:  ((20, [(2, 78)]),  (18, [(4, 31)]),   (18, [(2, 14), (4, 15)]),
         (26, [(4, 13), (1, 14)])),
    8:  ((24, [(2, 97)]),  (22, [(2, 38), (2, 39)]), (22, [(4, 18), (2, 19)]),
         (26, [(4, 14), (2, 15)])),
    9:  ((30, [(2, 116)]), (22, [(3, 36), (2, 37)]), (20, [(4, 16), (4, 17)]),
         (24, [(4, 12), (4, 13)])),
    10: ((18, [(2, 68), (2, 69)]), (26, [(4, 43), (1, 44)]),
         (24, [(6, 19), (2, 20)]), (28, [(6, 15), (2, 16)])),
}

# alignment pattern centre coordinates by version
ALIGN = {1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34],
         7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46], 10: [6, 28, 50]}

LEVELS = ['L', 'M', 'Q', 'H']
_LEVEL_BITS = {'L': 0b01, 'M': 0b00, 'Q': 0b11, 'H': 0b10}
_BITS_LEVEL = {v: k for k, v in _LEVEL_BITS.items()}

MASKS = [
    lambda i, j: (i + j) % 2 == 0,
    lambda i, j: i % 2 == 0,
    lambda i, j: j % 3 == 0,
    lambda i, j: (i + j) % 3 == 0,
    lambda i, j: (i // 2 + j // 3) % 2 == 0,
    lambda i, j: (i * j) % 2 + (i * j) % 3 == 0,
    lambda i, j: ((i * j) % 2 + (i * j) % 3) % 2 == 0,
    lambda i, j: ((i + j) % 2 + (i * j) % 3) % 2 == 0,
]


def size_of(version):
    return version * 4 + 17


# ------------------------------------------------------------------ GF(256)
_EXP = [0] * 512
_LOG = [0] * 256
_x = 1
for _i in range(255):
    _EXP[_i] = _x
    _LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def _mul(a, b):
    return 0 if a == 0 or b == 0 else _EXP[_LOG[a] + _LOG[b]]


def rs_generator(n):
    g = [1]
    for i in range(n):
        g2 = [0] * (len(g) + 1)
        for j, c in enumerate(g):
            g2[j] ^= c
            g2[j + 1] ^= _mul(c, _EXP[i])
        g = g2
    return g


def rs_encode(data, n):
    g = rs_generator(n)
    rem = [0] * n
    for d in data:
        factor = d ^ rem[0]
        rem = rem[1:] + [0]
        for i in range(n):
            rem[i] ^= _mul(g[i + 1], factor)
    return rem


# ------------------------------------------------------------- module layout
def function_mask(version):
    """True where a module is a function pattern (not data)."""
    n = size_of(version)
    f = [[False] * n for _ in range(n)]

    def block(r, c, h, w):
        for i in range(r, r + h):
            for j in range(c, c + w):
                if 0 <= i < n and 0 <= j < n:
                    f[i][j] = True

    for r, c in ((0, 0), (0, n - 8), (n - 8, 0)):        # finders + separators
        block(r, c, 8, 8)
    for i in range(n):                                    # timing
        f[6][i] = True
        f[i][6] = True
    for a in ALIGN[version]:                              # alignment
        for b in ALIGN[version]:
            if (a < 8 and b < 8) or (a < 8 and b > n - 9) or (a > n - 9 and b < 8):
                continue
            block(a - 2, b - 2, 5, 5)
    block(8, 0, 1, 9)                                     # format info
    block(0, 8, 9, 1)
    block(n - 8, 8, 8, 1)
    block(8, n - 8, 1, 8)
    if version >= 7:                                      # version info
        block(n - 11, 0, 3, 6)
        block(0, n - 11, 6, 3)
    return f


def data_positions(version):
    """Module coordinates in QR data order (bottom-right, upward zigzag)."""
    n = size_of(version)
    fn = function_mask(version)
    out = []
    col = n - 1
    upward = True
    while col > 0:
        if col == 6:
            col -= 1
        rows = range(n - 1, -1, -1) if upward else range(n)
        for r in rows:
            for c in (col, col - 1):
                if not fn[r][c]:
                    out.append((r, c))
        upward = not upward
        col -= 2
    return out


def format_positions(version):
    n = size_of(version)
    a = [(8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
         (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8)]
    b = [(n - 1, 8), (n - 2, 8), (n - 3, 8), (n - 4, 8), (n - 5, 8), (n - 6, 8),
         (n - 7, 8)] + [(8, n - 8 + i) for i in range(8)]
    return a, b


# --------------------------------------------------------------------- decode
def _read_format(grid, version):
    a, _ = format_positions(version)
    raw = 0
    for i, (r, c) in enumerate(a):          # a[0] is the MSB of the 15-bit word
        if grid[r][c]:
            raw |= 1 << (14 - i)
    f = raw ^ 0x5412
    level = _BITS_LEVEL[(f >> 13) & 0b11]
    mask = (f >> 10) & 0b111
    return level, mask, f


def decode(grid, version):
    """grid: n x n booleans in canonical orientation -> decoded bytes."""
    level, mask, _ = _read_format(grid, version)
    mfn = MASKS[mask]
    bits = []
    for r, c in data_positions(version):
        b = grid[r][c]
        if mfn(r, c):
            b = not b
        bits.append(1 if b else 0)
    codewords = [int(''.join(str(b) for b in bits[i:i + 8]), 2)
                 for i in range(0, len(bits) - 7, 8)]

    ec_per, layout = RS_TABLE[version][LEVELS.index(level)]
    blocks = []
    for count, dlen in layout:
        blocks += [dlen] * count
    # data codewords are interleaved across blocks
    data = [[] for _ in blocks]
    idx = 0
    for i in range(max(blocks)):
        for b, dlen in enumerate(blocks):
            if i < dlen:
                data[b].append(codewords[idx])
                idx += 1
    stream = [x for b in data for x in b]

    bitstr = ''.join(f'{x:08b}' for x in stream)
    mode = int(bitstr[0:4], 2)
    if mode != 4:
        raise ValueError(f'only byte mode supported, got mode {mode}')
    ln = int(bitstr[4:12], 2)
    out = bytearray()
    for i in range(ln):
        out.append(int(bitstr[12 + i * 8:20 + i * 8], 2))
    return bytes(out), level, mask


# --------------------------------------------------------------------- encode
def _bch_format(level, mask):
    f = (_LEVEL_BITS[level] << 3) | mask
    d = f << 10
    while d.bit_length() - 1 >= 10:
        d ^= 0x537 << (d.bit_length() - 11)
    return ((f << 10) | d) ^ 0x5412


def capacity(version, level):
    ec_per, layout = RS_TABLE[version][LEVELS.index(level)]
    return sum(c * d for c, d in layout)


def encode(data, version=None, level='M', mask=None):
    """-> (grid, version, level, mask). `data` is bytes."""
    if version is None:
        for v in sorted(RS_TABLE):
            if capacity(v, level) >= len(data) + 2:
                version = v
                break
        else:
            raise ValueError('data too long for versions 1-10')
    total_data = capacity(version, level)
    if len(data) + 2 > total_data:
        raise ValueError(f'{len(data)} bytes exceeds V{version}-{level} capacity')

    bits = '0100' + f'{len(data):08b}' + ''.join(f'{b:08b}' for b in data)
    bits += '0' * min(4, total_data * 8 - len(bits))          # terminator
    bits += '0' * (-len(bits) % 8)                            # byte align
    pad = ['11101100', '00010001']
    i = 0
    while len(bits) < total_data * 8:
        bits += pad[i % 2]
        i += 1
    codewords = [int(bits[i:i + 8], 2) for i in range(0, len(bits), 8)]

    ec_per, layout = RS_TABLE[version][LEVELS.index(level)]
    dblocks, eblocks = [], []
    pos = 0
    for count, dlen in layout:
        for _ in range(count):
            blk = codewords[pos:pos + dlen]
            pos += dlen
            dblocks.append(blk)
            eblocks.append(rs_encode(blk, ec_per))

    stream = []
    for i in range(max(len(b) for b in dblocks)):
        for b in dblocks:
            if i < len(b):
                stream.append(b[i])
    for i in range(ec_per):
        for b in eblocks:
            stream.append(b[i])
    allbits = ''.join(f'{x:08b}' for x in stream)

    n = size_of(version)
    grid = [[False] * n for _ in range(n)]
    _draw_function(grid, version)

    if mask is None:
        best = None
        for m in range(8):
            g = [row[:] for row in grid]
            _place(g, version, allbits, m)
            s = _penalty(g)
            if best is None or s < best[0]:
                best = (s, m, g)
        _, mask, grid = best
    else:
        _place(grid, version, allbits, mask)

    _draw_format(grid, version, level, mask)
    return grid, version, level, mask


def _draw_function(grid, version):
    n = size_of(version)

    def finder(r, c):
        for i in range(-1, 8):
            for j in range(-1, 8):
                if not (0 <= r + i < n and 0 <= c + j < n):
                    continue
                on = (0 <= i <= 6 and j in (0, 6)) or (0 <= j <= 6 and i in (0, 6)) \
                    or (2 <= i <= 4 and 2 <= j <= 4)
                grid[r + i][c + j] = on
    finder(0, 0)
    finder(0, n - 7)
    finder(n - 7, 0)
    for i in range(8, n - 8):
        grid[6][i] = i % 2 == 0
        grid[i][6] = i % 2 == 0
    for a in ALIGN[version]:
        for b in ALIGN[version]:
            if (a < 8 and b < 8) or (a < 8 and b > n - 9) or (a > n - 9 and b < 8):
                continue
            for i in range(-2, 3):
                for j in range(-2, 3):
                    grid[a + i][b + j] = max(abs(i), abs(j)) != 1
    grid[n - 8][8] = True                       # dark module


def _place(grid, version, bits, mask):
    mfn = MASKS[mask]
    for k, (r, c) in enumerate(data_positions(version)):
        b = bits[k] == '1' if k < len(bits) else False
        grid[r][c] = (not b) if mfn(r, c) else b


def _draw_format(grid, version, level, mask):
    f = _bch_format(level, mask)
    a, b = format_positions(version)
    for i, (r, c) in enumerate(a):
        grid[r][c] = bool((f >> (14 - i)) & 1)
    for i, (r, c) in enumerate(b):
        grid[r][c] = bool((f >> (14 - i)) & 1)


def _penalty(grid):
    n = len(grid)
    score = 0
    for line in list(grid) + [list(col) for col in zip(*grid)]:
        run = 1
        for i in range(1, n):
            if line[i] == line[i - 1]:
                run += 1
            else:
                if run >= 5:
                    score += 3 + (run - 5)
                run = 1
        if run >= 5:
            score += 3 + (run - 5)
    for r in range(n - 1):
        for c in range(n - 1):
            b = grid[r][c]
            if grid[r][c + 1] == b and grid[r + 1][c] == b and grid[r + 1][c + 1] == b:
                score += 3
    dark = sum(sum(1 for x in row if x) for row in grid)
    score += 10 * (abs(dark * 20 // (n * n) - 10))
    return score
