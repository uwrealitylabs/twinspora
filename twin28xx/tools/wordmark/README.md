# twin28xx back-silkscreen wordmark

Generates the `twin28xx` wordmark on `B.SilkS` as filled polygons.

- **twin** — [Instrument Serif](https://usemodify.com/fonts/instrument-serif/) Italic (OFL)
- **28xx** — [Pressuru](https://usemodify.com/fonts/pressuru/)

The glyphs are converted to outlines, so the board file has no font dependency —
nothing needs to be installed to open, plot, or fabricate it.

## Use

```sh
./make_wordmark.py --preview wm.png    # render only, board untouched
./make_wordmark.py --apply             # write into ../../twin28xx.kicad_pcb
./make_wordmark.py --apply --remove    # strip it back out
```

`--apply` replaces any wordmark already in the board (matched by the
`twin28xx wordmark` group), so edit `CONFIG` and re-run as often as you like.
A `.bak` is written next to the board unless you pass `--no-backup`.

Requires `fonttools`; `--preview` also needs `Pillow`.

## Knobs

Edit `CONFIG` at the top of `make_wordmark.py`, or override the common ones
on the command line:

```sh
./make_wordmark.py --twin-sy 1.4 --num-sx 1.3 --preview wm.png
```

| key | effect |
| --- | --- |
| `em_mm` | type size; everything scales from this |
| `twin_sx` / `twin_sy` | stretch "twin" — `sx < 1` condenses, `sy > 1` makes it taller and skinnier |
| `num_sx` / `num_sy` | stretch "28xx" — `sx > 1` makes it wider and fatter |
| `gap_em` | space between the two runs |
| `track_twin` / `track_num` | letterspacing within each run |
| `match_xheight` | keep Pressuru's `x` exactly as tall as the italic `n` (default on) |
| `pressuru_rel` | Pressuru's size relative to Instrument Serif — only used when `match_xheight=False` |
| `center` | placement on the board, mm |

`sy` scales about the baseline, so the two runs always sit on the same line.

### x-height matching

With `match_xheight=True` the Pressuru size is *solved for* at run time from the
real glyph outlines, so `28xx`'s lowercase `x` is exactly the height of `twin`'s
`n` no matter what you set `twin_sy` and `num_sy` to. Verified on the current
settings: `n` = 4.2666 mm, `x` = 4.2671 mm.

This falls out nicely — the same ratio also puts the `2`/`8` digits on the
italic's ascender line (5.325 mm vs the `t` at 5.342 mm), so the wordmark has one
x-height line and one cap line across both faces.

Don't hardcode `pressuru_rel` unless you want to break that. It was a fixed
constant at first, which silently desynced the moment `twin_sy` changed.

## knockout.py — text through the wordmark

Where a designator or the bible verse falls under the wordmark, both are white
silkscreen, so the text disappears into it. `knockout.py` computes the symmetric
difference (wordmark XOR text): overlapping ink is removed from *both*, so the
text reads dark-on-white inside the wordmark and white-on-dark outside.

```sh
./knockout.py --preview ko.png     # render only
./knockout.py --apply              # rewrite the wordmark polygons
./knockout.py --apply --remove     # undo
```

Any text item that *touches* the wordmark is converted to polygons in full, not
just its covered part — otherwise there would be a visible seam where a glyph
crosses the wordmark edge. That means the original text has to stop printing:
designators get `(hide yes)`, and `gr_text` (which has no hide flag) is cut out
and stashed. `knockout_state.json` records everything needed to reverse it,
including the pre-knockout wordmark outlines.

**Undo restores the board exactly** — verified at 0.000 µm coordinate deviation
across all 745 original points. Keep `knockout_state.json`; without it the undo
cannot run, and the wordmark's hand-applied scaling lives only in those saved
coordinates.

### How the text geometry is obtained

`kicad_text.py` reimplements KiCad's built-in `newstroke` stroke font and its
layout, so the knockout aligns with what pcbnew actually draws rather than an
approximation. Constants come from `common/font/stroke_font.cpp` and
`common/font/font.cpp`; the ASCII glyph table is extracted into
`newstroke_ascii.json`. Validated against `kicad-cli pcb export svg`: 0.973 IoU
over the whole layer, with every text item matching (the residual is sub-pixel
edge antialiasing on the artwork).

Two things that are easy to get wrong and are handled here: `bold` does **not**
add stroke width when an explicit `thickness` is set, and pen width is clamped to
0.25 x the smaller text dimension.

### Caveats

- The 19 affected designators are now polygons plus a hidden property. They no
  longer follow their footprints — if you move one of those parts, re-run
  `--remove`, move it, then `--apply` again.
- The knockout slot is as wide as the text stroke (0.15 mm). That is at the low
  end of what silkscreen holds open; ink spread can partly close it. `--grow`
  widens the slot, at the cost of thickening the same text where it sits outside
  the wordmark.
- Booleans are computed on a 150 px/mm raster (6.7 µm) and traced back to
  polygons with marching squares. Traced area matches the boolean to 0.007%.

## regen_qr.py — the back QR code

Regenerates the QR inside the `LOGO` footprint at (134.2, 126.5), keeping the
same position, 6.44 mm size and 33x33 module count so it drops into the same
spot.

```sh
./regen_qr.py --url https://github.com/uwrealitylabs/twin28xx --preview qr.png
./regen_qr.py --url https://github.com/uwrealitylabs/twin28xx --apply
```

`qr.py` is a small QR encoder (byte mode, versions 1-10, all ECC levels) — no
Python QR library was available. **Always verify a regenerated code with a real
scanner**; a structurally plausible QR that decodes to the wrong thing is the
failure mode to worry about. `qrread.swift` does this offline using macOS's
Vision framework:

```sh
swift qrread.swift qr.png       # -> DECODED: https://...
```

The current symbol was checked end-to-end: geometry re-extracted *from the board
file*, rendered mirrored as seen from the back, and decoded by Vision.

Current: V4-Q, mask 3, 41-byte payload, 195 µm modules. The previous symbol was
ECC level M; Q was chosen for more error-correction headroom at the same physical
size, which is worth having at this module pitch. Note 195 µm is close to the
0.15 mm silkscreen minimum — if a fab struggles with it, drop to a shorter URL so
a lower version fits, rather than shrinking the modules further.

## Fit and manufacturability

The current settings were chosen against the free space on the back:

- **23.9 mm** is the widest the wordmark can be — the band between the top board
  edge and the QR/text row is what constrains it, in both axes. `em_mm` is set to
  the largest value that stays inside it.
- Clearance to the nearest pad, existing silk, or board edge: **0.35 mm**.
- Ink thinner than 0.15 mm: **0.10%**, confined to the tapered tips of the
  italic's terminals. No sustained stroke is under the minimum.

Because the total width is capped, `num_sx` trades against `em_mm`: widening
`28xx` shrinks everything else to compensate, which thins the italic's hairlines.
At `num_sx=1.25` the em drops to 5.72 mm and sub-0.15 mm ink rises to 1.13%.
`num_sx=1.0` is the current setting for that reason — with the x-heights matched,
Pressuru is already 25% larger than it was, so it reads heavy without the stretch.

Worth knowing when you retune: **condensing** "twin" (`twin_sx < 1`) thins its
hairlines and hurts printability fast — at `twin_sx=0.85` the sub-0.15 mm ink
jumps to ~0.6%. **Stretching it vertically** (`twin_sy > 1`) makes it read
skinnier while slightly *thickening* those hairlines, so prefer `twin_sy` over
`twin_sx` for that effect.

The `8` counters are held open with zero-width bridges into the outer ring, the
same technique the existing logo polygons on this board use.
