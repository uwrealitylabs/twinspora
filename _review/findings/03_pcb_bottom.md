# PCB Bottom-Side Pre-Fab Review (v2) — `twin28xx.kicad_pcb`

Reviewed: 2026-05-05 (re-do with primary-source verification)
Source: `D:\gehub\twin28xx\twin28xx\twin28xx.kicad_pcb`
Stats: 76.95 × 36.925 mm, 4-layer, 1.6167 mm thick (`_review/stats.json`).
Per `stats.json`: front-density 37.04 %, back-density 9.59 %, **0 components** on the back layer (`components.smd.back = 0`, `components.tht.back = 0`, `components.unspecified.back = 0`).

---

## Corrections to prior version (`v1_archive/03_pcb_bottom.md`)

| # | Prior claim | Correction (with primary-source citation) |
|---|---|---|
| 1 | "Magnet → encoder die distance is now FR4 (1.62 mm) + QFN-16 package thickness (~0.85 mm) ≈ 2.5 mm. MT6701 datasheet operating range is ~1–3 mm but signal magnitude … degrades sharply past ~2 mm." | **Wrong on both numbers.** MT6701 datasheet (MagnTek Rev.1.5, 2021.03 / Rev.1.8, 2022.12) §5 "Magnetic Input Specifications", page 8, parameter **AG (Air Gap, Magnetic to IC Surface Distance)**: **Min 0.5 mm, Typ 1.0 mm, Max 2.0 mm**. The "operating range" is 0.5–2.0 mm, not 1–3 mm. QFN-16 package thickness from §9.2 (page 33), parameter **A**: **0.700–0.800 mm** (max), not 0.85 mm. The realistic stack-up is 1.617 mm FR4 + ~0.75 mm package ≈ **2.37 mm**, which **exceeds the datasheet AG_max (2.0 mm) by ~0.37 mm — the part is operating *outside its specified magnetic-input range*, not "at the upper limit."** |
| 2 | "/SPI1_MISO 0.16 mm at (93.25, 117.41)→(97.41, 117.41) within ±2.5 mm of U18 die" | Re-measured: closest distance from U18 center (95.000, 120.0275) to the /SPI1_MISO segment is **2.621 mm** (just outside 2.5 mm). The /TIM8_CH3N segment is 2.028 mm. The /SPI1_MISO concern as stated overshot by ~0.1 mm. Real worst-offenders (re-listed in B3): /TIM8_CH2 at **0.617 mm** (clipping the courtyard) and /TIM8_CH3 at 1.819 mm. |
| 3 | "no keepout/anti-pad is defined under the MT6701 die" | True, **but verify the KiCad construct**. The two `(keepout …)` blocks at lines 66599 and 82824 in `twin28xx.kicad_pcb` are *placement-rule areas* (`auto-placement-area-/motor_driver/`, `auto-placement-area-/motor_driver1/`) with `tracks/vias/pads/copperpour/footprints` all set to `allowed`. They are NOT copper exclusions and do nothing to clear the GND pour. Confirmed there is no `(rule_area)` or copper keepout anywhere in the file. |
| 4 | "MT6701/AS5048 designs is a circular copper keepout of at least 5–6 mm diameter" | The MT6701 datasheet (Rev 1.5 / 1.8) **does not specify a copper keepout** anywhere in the document. There is no mention of "keepout", "PCB layout", or copper near the magnetic path. The datasheet only specifies AG and Bpk as measured at the IC surface. The "5–6 mm keepout" recommendation is **not from MagnTek's datasheet** — sourced rule of thumb only and removed from this review. |
| 5 | "MT6701 QFN-16 package thickness ~0.85 mm" | MT6701 §9.2 gives **A = 0.700–0.800 mm** (typ ~0.75 mm), not 0.85 mm. |

The two trace-routing and GND-fill structural findings (B2, B3) and the no-cutout finding (C1) survive intact. The headline "wrong-side encoder" finding (B1) is *strengthened*, not weakened: the gap is **above** the datasheet maximum, not at the limit.

---

## Datasheet citations (primary sources, this review)

- MT6701 — MagnTek MT6701 Hall-Based Angle Position Encoder Sensor.
  - Rev.1.5, 2021.03 (English, 36 pp). Mirrored at https://uploadcdn.oneyac.com/attachments/files/brand_pdf/magntek/F3/CA/MT6701QT-STD.pdf — local copy at `D:\gehub\twin28xx\_review\datasheets\MT6701_alt_MT6701QT-STD.pdf`. The footprint's own `Datasheet` property in `twin28xx.kicad_pcb` (lines 6647 and 13158) references **Rev.1.5**, so this is the working revision.
  - Rev.1.8, 2022.12 (Chinese, 36 pp). Direct from MagnTek: https://www.magntek.com.cn/upload/pdf/202312/MT6701_Rev.1.8_中文版.pdf — local copy at `D:\gehub\twin28xx\_review\datasheets\MT6701_Rev1.8.pdf`. Spec values for AG and Bpk are identical between Rev 1.5 and Rev 1.8.
  - **§5 "Magnetic Input Specifications" / "外加磁场参数", page 8/9** — verbatim:
    - `Bpk` (Magnetic Input Field Amplitude, "Measure at the IC Surface"): **Min 200, Max 1,000, Unit Gauss**.
    - `AG` (Air Gap, "Magnetic to IC Surface Distance"): **Min 0.5, Typ 1.0, Max 2.0, Unit mm**.
    - `Dmag`: typ 6.0 mm; `Tmag`: typ 2.5 mm; `DISP` (off-axis misalignment): max 0.3 mm.
  - **§1.2 / Figure 2 "Pin Configuration for QFN-16 Package", page 4** — Sensing Center is at the geometry center of the package (annotation "Sensing Center at Geometry Center" on top-view diagram).
  - **§2 "Functional Diagram" + Figure 3, page 5** — "uses advanced magnet sensing technology to sense the magnetic field distribution across the surface of the chip … delivers a voltage representation of the magnetic field at the surface of the IC." Confirms the AG reference plane is the chip top surface (under mold compound, package-top side).
  - **§9.2 "QFN-16 Package", page 33** — package outline:
    - `A` (overall height): Min 0.700, Max 0.800 mm.
    - `A1` (standoff): 0.000–0.050 mm.
    - `D × E` (body): 2.900–3.100 mm × 2.900–3.100 mm.
    - `D1 × E1` (EP exposed pad): 1.600–1.800 × 1.600–1.800 mm.
    - `e` (pitch): 0.500 mm REF; `b` (lead width): 0.180–0.300 mm.
  - **What the datasheet does NOT cover**: through-PCB sensing, copper keepout, ground-plane attenuation, or eddy-current effects from intervening copper. There is no PCB-layout / app-note section in this datasheet. Any claim about copper keepouts under the encoder is therefore **NOT** datasheet-supported.

---

## BLOCKERS

### B1 — MT6701 magnetic encoders are placed on the WRONG side of the board (F.Cu instead of B.Cu) — sense gap exceeds AG_max

The README states the motors mount on the back of the PCB; the rotor's diametric magnet is therefore on the back side. The MT6701 sensing center is at the package-top (`§1.2`, Figure 2 "Top View"), and AG is measured from the magnet to the IC surface (`§5`).

What the file actually shows:

| Designator | Footprint | Layer | Center (mm) | Source line |
|---|---|---|---|---|
| U18 | `Package_DFN_QFN:QFN-16-1EP_3x3mm_P0.5mm_EP1.7x1.7mm` | **F.Cu** | (95.000001, 120.0275) | `twin28xx.kicad_pcb` 6618–6624 |
| U16 | same | **F.Cu** | (135.000001, 120.0275) | `twin28xx.kicad_pcb` 13129–13135 |

Pads of both parts are on `F.Cu` / `F.Mask` / `F.Paste`; silk, courtyard, and fab on `F.SilkS` / `F.CrtYd` / `F.Fab`. Independently confirmed by `stats.json`: `components.smd.back = 0`. Bottom-side `B.Paste`, `B.Courtyard`, and `B.Fab` SVG exports contain only board-outline plus drill apertures.

**Sense-path geometry** (encoder on F.Cu, magnet on the rotor below B.Cu):

| Stack-up element | Thickness (mm) | Source |
|---|---|---|
| FR4 board (full thickness) | 1.6167 | `stats.json` `board.board_thickness` |
| QFN-16 package height (max) | 0.800 | MT6701 §9.2 (Rev 1.5 page 33) |
| QFN-16 package height (typ) | ~0.750 | midpoint of `A = 0.700–0.800` |
| (`A3` die-paddle thickness 0.203 REF; the sensing element is at die top surface internal to the package) | — | MT6701 §9.2 |

**Magnet → IC-surface distance**: 1.617 + (typ 0.75) ≈ **2.37 mm** (with worst-case package: 1.617 + 0.800 = **2.42 mm**).

**MT6701 AG_max from §5 = 2.000 mm.** The realised gap is **0.37–0.42 mm above the datasheet maximum** — the part will be operated outside its specified magnetic-input range. Bpk at the IC surface will fall well below 200 Gauss for any normal NdFeB diametric magnet (a 6×2.5 mm N35 puck typically gives ~150–250 G at 2 mm and continues falling steeply with z). Outcomes likely: marginal or asserted "Bpk-too-weak" status flag (`Mg[3:0]` field, MT6701 §7 / register-map page 27), elevated angle noise, large temperature drift (`TCmag1 = -0.12 %/°C` for NdFeB, §5). Not waivable in firmware; this is a magnetic-air-gap deficiency.

**Fix**: move U16 and U18 to B.Cu (mirror about the board), or change the mechanical scheme so the magnet sits on the F.Cu side at ≤2.0 mm AG.

### B2 — Continuous GND copper pour passes directly under both encoder sense paths on every relevant layer

Zone `In1.GND` (`twin28xx.kicad_pcb` line 66621) is filled on **F.Cu, B.Cu, In1.Cu, In2.Cu** with a polygon (75.80, 96.55) → (75.78, 138.95) → (156.78, 138.95) → (157.78, 93.45) — i.e. the entire active region. The two `(keepout …)` blocks at lines 66599 and 82824 are KiCad *placement* rule areas, not copper exclusions (all five `allowed` flags). No copper keepout exists anywhere in the file.

Geometric verification (script `_review/datasheets/_check_zone.py`): the encoder centers (95.000, 120.0275) and (135.000, 120.0275) lie inside `In1.GND` filled-polygons on **F.Cu, In1.Cu, and B.Cu**. (On In2.Cu the GND polygon does not cover those points because In2.Cu is dominated by VCC zones — but VCC copper is just as opaque to magnetic flux.) Thus continuous copper sits on every metal layer between the magnet and the encoder die.

The MT6701 datasheet (Rev 1.5 / 1.8) does **not specify** copper-clearance requirements under the sensor. However: any conductor in the magnetic-flux path will (a) attenuate static field and (b) generate eddy currents under the rotating diametric field. Standard practice for axial Hall encoders is to remove copper from a circular region under the package on every layer; **this practice is not codified in the MT6701 datasheet**, so the recommendation here is engineering judgement, not a datasheet rule. The empirical risk is nonetheless real and additive to B1's gap problem.

**Fix**: after relocating to B.Cu (B1), add a circular `(zone … keep_out)` rule-area centered on each encoder die, on F.Cu / In1.Cu / In2.Cu / B.Cu, of diameter at least the magnet diameter (Dmag = 6.0 mm typ per §5) plus margin — 6–8 mm typical.

### B3 — High-frequency switching traces routed within the encoder courtyard on B.Cu (re-measured)

Re-measured with `_review/datasheets/_check_traces.py` (regex finds segments with either `(net "name")` or `(net N)` form; v1's listing missed some endpoints).

**Within 2.5 mm radius of U18 center (95.000, 120.0275) on B.Cu:**

| Net | Width (mm) | Min distance to U18 center (mm) | Notes |
|---|---|---|---|
| `/TIM8_CH2` | 0.20 | **0.617** | 3 segments. Endpoint at (93.200, 119.100) clips the SW corner of the 3×3 mm package. PWM gate-drive to driver #2 — fast-switching. |
| `/TIM8_CH3` | 0.20 | 1.819 | 2 segments — within die. Gate-drive PWM. |
| `/TIM8_CH3N` | 0.20 | 2.028 | 1 segment under courtyard. Complementary gate drive (hard switch). |

**Within 6 mm of U18 center (B.Cu) — adjacent fast nets:** /SPI1_MISO 2.621, /SPI1_MOSI 3.278, /SPI1_NSS 4.148, /SPI1_SCK 3.788, /SPI2_MISO 4.388, /SPI2_NSS 4.096, /TIM8_CH1 5.178, /TIM8_CH1N 4.778, /TIM8_CH2N 5.627.

**Within 2.5 mm radius of U16 center (135.000, 120.0275) on B.Cu:**

| Net | Width (mm) | Min distance (mm) | Notes |
|---|---|---|---|
| `/RESET` | 0.16 | 1.748 | MCU reset — quasi-static, low concern. |
| `/BOOT` | 0.16 | 2.284 | Boot mode — quasi-static, low concern. |

U16 is significantly cleaner than U18 because the second motor-driver IC is on the opposite side of the board and its TIM1_CHx PWM does not crowd U16. U18 carries all three TIM8 phases through its courtyard.

**Fix**: re-route /TIM8_CH2, /TIM8_CH3, /TIM8_CH3N off the encoder die area before B.Cu becomes the encoder sense path (B1). The relocation in B1 forces this cleanup anyway: with the encoder pads moving to B.Cu, the existing B.Cu signal traces *must* be moved.

---

## CRITICAL

### C1 — No motor-shaft cutout / clearance hole in `Edge.Cuts`

`Edge.Cuts` contains one rectangular outline (8 elements: 4 lines + 4 R3.4 mm corner arcs) at lines 45476–45558 of `twin28xx.kicad_pcb`. Corners at (76.525, 100.8) → (153.475, 137.725). **No interior cutouts**. The 1 mm `gr_circle` rings at the encoder centers are on `B.SilkS`, not `Edge.Cuts` — they are silkscreen alignment targets only.

For GM2804 / GL-30 motor mounting on the back: the rotor face sits ~1–3 mm below the PCB; the magnet (Dmag 6.0 mm × Tmag 2.5 mm per MT6701 §5) on the rotor would pass through that air gap. With AG_max 2.0 mm and current stack-up 2.37 mm (B1), the only way to bring the magnet within spec — without moving encoders to B.Cu — is to inset the magnet through the PCB via a cutout. Verify mechanical drawing for the chosen motor and decide between (a) moving encoders to B.Cu (B1) and a small recess, (b) thinning the PCB so 1 mm FR4 + ~0.75 mm package gives sub-2 mm AG, or (c) a Ø6–10 mm cutout under each encoder so the magnet protrudes into the board cavity.

### C2 — Motor-mounting hole pattern: M3 corners + M2 inner-row, double-stacked with SMD spacers — DRC flagging this as a hole/mask conflict

Mounting holes (footprints on F.Cu):

| Designator | Type | Position (mm) |
|---|---|---|
| H1 | M3 PTH 3.2 mm + Pad/Via | (80.0, 104.25) |
| H4 | M3 PTH 3.2 mm + Pad/Via | (80.0, 134.25) |
| H7 | M3 PTH 3.2 mm + Pad/Via | (150.0, 134.25) |
| H10 | M3 PTH 3.2 mm + Pad/Via | (150.057, 104.25) — 0.057 mm asymmetry |
| H8 | M2 DIN965 Pad | (80.0, 110.0) |
| H11 | M2 DIN965 Pad | (80.0, 120.0) |
| H2 | M2 DIN965 Pad | (150.0, 110.0) |
| H5 | M2 DIN965 Pad | (150.0, 120.1) — 0.1 mm asymmetry |
| H3, H6, H9, H12 | SMD standoff (`Mechanical:SMD_BD5.6-D3.6`, `SMTSOM225BTR`) | concentric on H1/H4/H7/H10 |

The SMD standoffs sit directly on top of the M3 PTH pads. KiCad-DRC flags **33 hole-to-hole**, **18 hole-clearance**, **8 solder-mask-bridge**, **16 padstack-invalid**, **4 npth-inside-courtyard**, and **13 holes-co-located** errors arising from this stack. This appears intentional (the standoff lands on the M3 GND ring) but the error list is large; either negotiate fab acceptance and document waivers, or convert the SMD standoffs to dedicated annular pads with no hole-coincidence. Tighten H10 X to 150.000 and H5 Y to 120.000.

### C3 — Bottom silkscreen mirror-text labels for FRONT components

Multiple F.Cu components have their `Reference` text property forced onto `B.SilkS` with `(justify mirror)`. After fabrication, anyone looking at the back face will see designator labels (R28, R23, R24, R21, C40–C42, C53–C58, C37–C39, C43, C44, C51–C56, U4, U5, R5, R27, LED1, …) without parts to label. Examples: C40 footprint at line 3302–3303 is on F.Cu but its Reference at 3308–3318 is on `B.SilkS`.

Likely root cause: the design was authored with a "back-facing" silk convention that didn't move the actual footprints. Fix is forced by the resolution of B1: when the encoders move to B.Cu, also audit which other parts should follow (e.g. the two motor drivers and bypass caps may be intended for B.Cu too). Otherwise move `Reference` text back to `F.SilkS`.

### C4 — Bottom layer carries hard-switching motor PWM gate-drive signals

Beyond the encoder area (B3), `TIM1_CHx` and `TIM8_CHx` and `SPIx_*` lines route significantly on B.Cu at 0.16–0.20 mm widths. Approximate B.Cu segment widths:

```
0.16 mm :  212
0.20 mm :  168
0.25 mm :    3
0.30 mm :   90
0.80 mm :   10  (mostly /5V_BKOUT and /BUCK)
```

GND pour on B.Cu is interrupted by these traces; verify return-current paths for /PHA1, /PHB1, /PHC1, /PHA2, /PHB2, /PHC2 (these are routed as zones, not segments — In2.Cu carries +BATT and VCC zones, In1.GND on F.Cu / B.Cu / In1.Cu / In2.Cu).

### C5 — DRC: 84 errors / 635 warnings + 1 unconnected_items + 11 schematic-parity warnings

From `_review/drc.json` (re-summarized via `_drc_summary.py`):

- **unconnected_items (error, 1)**: `Pad 1 [/VCP] of TP46`. Test point — verify intent.
- **clearance (error, 1)**: 0.1895 mm (constraint 0.2 mm) between via and PTH pad 2 [/PHB1] of J9.
- **copper_edge_clearance (error, 7)**: 0.175 mm vs 0.2 mm — affects J5 pads 5/6 [GND], J1 pads 4/5 [GND], U5 pad 2 [GND], C43 pad 2 [VCC], C57 pad 2 [VCC]. Pull pads in 0.05 mm.
- **solder_mask_bridge (error, 8)**, **hole_clearance (error, 18)**, **hole_to_hole (error, 33)**, **padstack_invalid (error, 16)**, **npth_inside_courtyard (error, 4)**, **holes_co_located (error, 13)** — almost all caused by H3/H6/H9/H12 SMD standoffs concentric over H1/H4/H7/H10 M3 PTH (see C2).
- **starved_thermal (error, 12)**: GND zone has only 1 spoke into J5/U9/C23/C8/C4/X1/C60/C14/U7/C59/R5 instead of min 2.
- **courtyards_overlap (error, 18)**.
- **schematic_parity (warning, 11)**: footprint_symbol_mismatch on FID1/FID2/FID3 and the four mounting holes (warnings — non-blocking).

Total violations: 719 (84 error, 635 warning). Top warning types: silk_over_copper 199, text_height 192, silk_overlap 118, lib_footprint_mismatch 46, silk_edge_clearance 31.

---

## NITS / Style

- **N1** — `B.Fab` and `B.Courtyard` SVG/PNG exports are empty save board outline + drill apertures. Will populate when encoders move to B.Cu (B1).
- **N2** — `H10` X is 150.057 mm (line 29367) instead of 150.000; `H5` Y is 120.1 mm (line 27191) instead of 120.0. Tighten to grid.
- **N3** — Reference designator text size 0.6 × 0.8 mm with 0.15 mm thickness — `text_height` warning fires 192× in DRC. Readable on most fabs but at silk-floor.
- **N4** — `silk_over_copper` 199×, `silk_overlap` 118× — visually cluttered but expected on dense layouts.
- **N5** — `lib_footprint_mismatch` 46× — run "Update footprints from library" before tape-out.
- **N6** — `track_dangling` (warning) 2× — likely related to floating /VCP test point.
- **N7** — `B.SilkS` `gr_circle` rings (lines 45454, 45465) at 1 mm radius on encoder centers — useful as magnet-alignment targets *after* B1 moves the parts to B.Cu.

---

## Notes / Confirmations

- Edge.Cuts: outer rectangle only, 76.95 × 36.925 mm (lines 45476–45558), R3.4 mm corners. No interior cut-outs (C1).
- USB-C (J2) is reflow SMT (`USB-C_SMD-TYPE-C-31-M-12_1`).
- `B.Mask` SVG: only mask openings around through-hole / PTH pads (mounting holes, BK22 power connectors, J9/J10 power terminals, USB shield). No fine-pitch back-side mask apertures because there are no back-side parts. Re-verify after B1.
- `B.Paste` SVG: empty save apertures around PTH/connector pads. Re-export and verify after B1.
- Drill table from `stats.json`: 520 vias @ 0.30 mm, 87 vias @ 0.40 mm, 32 PTH @ 0.50 mm, 8 @ 1.0 mm, 6 @ 1.4 mm, 4 PTH @ 3.2 mm (M3), 4 NPTH @ 3.8 mm, 3 NPTH @ 0.99 mm, 2 NPTH 0.75 mm, 4 PTH @ 2.2 mm. Min drill 0.30 mm. Min track width 0.16 mm. Min track clearance 0.1998 mm.
- 4 fiducials (FID1/FID2/FID3 visible; FID4 implied) — adequate for assembly.
- BOM: C44, C58 = `50PX330MEFC10X16` THT bulk caps; C43, C57 = `EEEFT1H331GP` SMD bulk caps.

---

## Verification scripts created in this re-review

- `D:\gehub\twin28xx\_review\datasheets\_extract_mt6701.py` — pdftotext via PyMuPDF, used to extract MT6701 PDF text.
- `D:\gehub\twin28xx\_review\datasheets\_check_traces.py` — distance-from-segment scan for B.Cu and F.Cu nets near U16 / U18 centers.
- `D:\gehub\twin28xx\_review\datasheets\_check_zone.py` — point-in-polygon test for `In1.GND` filled polygons on each layer at the encoder centers.
- `D:\gehub\twin28xx\_review\datasheets\_drc_summary.py` — DRC by-severity / by-type summary.

Datasheets cached locally:
- `D:\gehub\twin28xx\_review\datasheets\MT6701_alt_MT6701QT-STD.pdf` (Rev 1.5 EN, 36 pp).
- `D:\gehub\twin28xx\_review\datasheets\MT6701_Rev1.8.pdf` (Rev 1.8 CN, 36 pp).
