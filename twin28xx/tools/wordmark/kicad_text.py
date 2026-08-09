"""Render KiCad stroke text (the built-in "newstroke" font) to polylines in board mm.

Reproduces KiCad's own layout so the geometry lines up exactly with what pcbnew
draws. Constants and algorithm follow common/font/stroke_font.cpp and
common/font/font.cpp in the KiCad source.
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))

STROKE_FONT_SCALE = 1.0 / 21.0
FONT_OFFSET = -8
INTERLINE_PITCH = 1.68          # METRICS::m_InterlinePitch
LEGACY_FACTOR = 0.9583          # STROKE_FONT::GetInterline
FIRST_LINE_FUDGE = 1.17         # font.cpp getLinePositions
ITALIC_TILT = 1.0 / 8


def effective_pen(thickness, size):
    """KiCad's effective pen width (eda_text.cpp).

    An explicit thickness wins outright — `bold` only matters when thickness is
    unset — and the result is clamped to 0.25 x the smaller text dimension.
    """
    return min(thickness, min(size) * 0.25)


class StrokeFont:
    def __init__(self, path=None):
        raw = json.load(open(path or os.path.join(HERE, 'newstroke_ascii.json')))
        self.glyphs = []        # (strokes, width) per glyph, index = ord(c) - 32
        for entry in raw:
            self.glyphs.append(self._parse(entry))

    @staticmethod
    def _parse(entry):
        start = (ord(entry[0]) - ord('R')) * STROKE_FONT_SCALE
        end = (ord(entry[1]) - ord('R')) * STROKE_FONT_SCALE
        width = end - start
        strokes, cur = [], []
        for i in range(2, len(entry) - 1, 2):
            a, b = entry[i], entry[i + 1]
            if a == ' ' and b == 'R':
                if len(cur) > 1:
                    strokes.append(cur)
                cur = []
            else:
                cur.append(((ord(a) - ord('R')) * STROKE_FONT_SCALE - start,
                            (ord(b) - ord('R') + FONT_OFFSET) * STROKE_FONT_SCALE))
        if len(cur) > 1:
            strokes.append(cur)
        return strokes, width

    def glyph(self, ch):
        i = ord(ch) - 32
        if i < 0 or i >= len(self.glyphs):
            i = ord('?') - 32
        return self.glyphs[i]

    def line_width(self, text, size_x, italic=False):
        w = 0.0
        for ch in text:
            w += self.glyph(ch)[1] * size_x
        return w

    def render(self, text, at, size, thickness, angle=0.0, justify_h='center',
               justify_v='center', mirror=False, italic=False, line_spacing=1.0):
        """-> list of polylines (each a list of (x, y) in board mm).

        `size` is (size_x, size_y) as stored in KiCad, `at` the text anchor.
        """
        ox, oy = at
        sx, sy = size
        lines = text.replace('\\n', '\n').split('\n')
        interline = sy * INTERLINE_PITCH * LEGACY_FACTOR * line_spacing
        height = sy * FIRST_LINE_FUDGE + (len(lines) - 1) * interline

        off_x = thickness / 1.52
        off_y = sy - thickness * 0.052
        if justify_v == 'center':
            off_y -= height / 2
        elif justify_v == 'bottom':
            off_y -= height

        tilt = ITALIC_TILT if italic else 0.0
        out = []
        for li, line in enumerate(lines):
            lw = self.line_width(line, sx, italic)
            lx = off_x
            if justify_h == 'center':
                lx = -lw / 2
            elif justify_h == 'right':
                lx = -(lw + off_x)
            ly = off_y + li * interline

            cursor = lx
            for ch in line:
                strokes, gw = self.glyph(ch)
                for st in strokes:
                    pts = []
                    for px, py in st:
                        x = px * sx
                        y = py * sy
                        if tilt:
                            x -= y * tilt
                        pts.append((x + cursor, y + ly))
                    out.append(pts)
                cursor += gw * sx

        # anchor-relative -> board, with mirror then rotation about the anchor
        a = math.radians(angle)
        ca, sa = math.cos(a), math.sin(a)
        final = []
        for pts in out:
            tp = []
            for x, y in pts:
                if mirror:
                    x = -x
                tp.append((ox + x * ca + y * sa, oy - x * sa + y * ca))
            final.append(tp)
        return final
