# PCB Top-Side Review (v2 — primary-source verified)

Twinspora dual BLDC, 76.95 x 36.93 mm, 4-layer.
Verified 2026-05-05 against:

- TI DRV8316C datasheet **SLVSH07** (Dec 2022), pages 5, 19, 82, 83, 84.
- Direct parse of `D:\gehub\twinspora\twinspora\twinspora.kicad_pcb` (segments, vias, footprints, pad-net resolution after rotation).
- `D:\gehub\twinspora\_review\drc.json` (KiCad 10.0.1 generated 2026-05-05 16:56).
- `D:\gehub\twinspora\_review\stats.json`.
- Visual inspection of `D:\gehub\twinspora\_review\datasheets\drv8316c_p84_layout_zoom.png` (rendered crop of TI Layout Example, sec 11.2).
- Visual inspection of `D:\gehub\twinspora\_review\exports\layers\F.Silkscreen.pdf` and `D:\gehub\twinspora\_review\exports\3d\top.png`.

Stackup re-confirmed from kicad_pcb lines 29-98:

```
F.Cu     35   um  (1 oz)
prepreg  210  um  NP-155F 7628, er 4.4
In1.Cu   15.2 um  (~0.5 oz)
core     1065 um  NP-155F core, er 4.43
In2.Cu   15.2 um  (~0.5 oz)
prepreg  210  um  NP-155F 7628, er 4.4
B.Cu     35   um  (1 oz)
```

`min_track_width = 0.16 mm`, `min_drill = 0.30 mm`, `min_track_clearance = 0.20 mm` per stats.json. No impedance control specified in `tuning_profiles`.

DRC totals (drc.json): 1 clearance, 18 hole_clearance, 7 copper_edge_clearance, 18 courtyards_overlap, 4 npth_inside_courtyard, 8 solder_mask_bridge, 12 starved_thermal, 16 padstack_invalid, 13 holes_co_located, 33 hole_to_hole, 2 track_dangling, 1 unconnected_items, plus 199 silk_over_copper / 192 text_height / 118 silk_overlap / 31 silk_edge_clearance / 46 lib_footprint_mismatch (cosmetic).

---

## BLOCKERS

### B1 — Bulk electrolytic pads C43 and C57 overhang the top board edge (0.000 mm clearance)

Re-verified from drc.json (`copper_edge_clearance`):

- `Pad 2 [VCC] of C43` at (109.000, 102.405) — actual edge clearance **0.0000 mm** to top Edge.Cuts segment (y=100.800).
- `Pad 2 [VCC] of C57` at (123.700, 102.405) — actual edge clearance **0.0000 mm**.

Footprint = `Capacitor_SMD_UWRL:CAP-SMD_BD10.0-L10.3-W10.3-LS11.0-R-RD` (kicad_pcb L18616). Both are EEEFT1H331GP 330 µF SMD electrolytics. The pad edges sit exactly on the route line; any V-cut/router tolerance will cut into copper.

**Action:** shift C43 and C57 ≥1 mm interior (decrease Y), or rotate 90° so the long axis is parallel to the edge.

### B2 — GND via 0.190 mm from J9 PHB1 motor pad

drc.json `clearance` (only one in the project): Via [GND] at **(136.500, 101.950)** → PTH pad 2 [/PHB1] of J9 at **(135.750, 103.149)**, actual 0.1895 mm vs 0.2000 mm rule. At 24 V this is electrically fine but with ±0.05-0.10 mm drill registration the GND drill can shave the J9 pin barrel.

**Action:** move via ≥0.3 mm or shift J9.

### B3 — J5 / J1 GND pads 0.175-0.196 mm from bottom Edge.Cuts

drc.json `copper_edge_clearance`, edge segment at y=137.725:

- Pad 5 [GND] of J5 (144.200, 136.400) — 0.1750 mm
- Pad 6 [GND] of J5 (138.900, 136.400) — 0.1750 mm
- Pad 4 [GND] of J1 (137.099, 136.529) — 0.1961 mm
- Pad 5 [GND] of J1 (132.498, 136.529) — 0.1961 mm

Same family as B1 but bottom-side connectors.

**Action:** shift J5 and J1 ≥0.3 mm up.

### B4 — U5 (TVS) GND pad 0.165 mm from top Edge.Cuts (newly flagged)

Not called out in the prior review. `Pad 2 [GND] of U5 on F.Cu` at (115.600, 101.665), edge clearance **0.1649 mm** to top Edge.Cuts at y=100.800 (drc.json `copper_edge_clearance`). Same fab risk family as B1/B3.

**Action:** move U5 ≥0.4 mm interior.

### B5 — 9 stacked GND vias on U15 EP and U7 (drilled holes co-located, real fab error)

Re-grepped from .kicad_pcb: 26 raw `(via ...)` entries inside the U15 EP bounding box but only **18 unique XY positions** — 8 positions have **two stacked vias** (identical XY, identical 0.45/0.30 size/drill, identical net "GND"). Coordinates (drc.json `holes_co_located`):

```
(91.750, 108.750), (91.750, 111.750), (93.750, 108.750), (93.750, 111.750),
(92.750, 108.750), (92.750, 111.750), (90.750, 108.750), (90.750, 111.750)
```

This is genuine duplicate via geometry — the file has two `(via ...)` blocks at each of these eight positions. Plus one more pair at (115.600, 132.600) under U7. Total 9 stacked-via DRC errors. The fab will drill each hole twice (or fail outright). The U14 EP does **not** have this problem (18 unique positions, 18 vias).

**Action:** delete the duplicate via at each of the 9 listed XYs. This single fix closes 9 of the 13 `holes_co_located` errors.

---

## CRITICAL

### C1 — DRV8316C ceramic decoupling caps too far from VM / CPH-CPL pins

**Primary source — TI DRV8316C datasheet, page 5 ("Pin Functions"):**
> VM ... bypass to PGND with two 0.1-µF capacitors (for each pin) plus one bulk capacitor rated for VM.
> CP ... Connect a X5R or X7R, 1-µF, 16-V ceramic capacitor between the CP and VM pins.
> CPH/CPL ... Connect a X5R or X7R, 47-nF, ceramic capacitor between the CPH and CPL pins.

**Primary source — TI DRV8316C datasheet, page 83 (sec 11.1 Layout Guidelines):**
> Small-value capacitors such as the charge pump, AVDD, and VREF capacitors should be ceramic and placed closely to device pins.

The datasheet does not state a numeric distance, but the TI Layout Example (sec 11.2, page 84, rendered as `drv8316c_p84_layout_zoom.png`) shows the 0.1 µF VM caps, the 47 nF CPH/CPL fly cap and the AVDD cap **immediately adjacent** to the package, all within ~1× package-pin pitch (≈ 1-2 mm of the relevant pin).

On Twinspora I measured (after 90° rotation transformation of pad-local to global coordinates):

| Cap | Value (verified) | Function | Position | Nearest VM pin | Nearest CPH/CPL pin |
|---|---|---|---|---|---|
| **C36** | 0402 100 nF X7R 50 V (CL05B104KB54PNC) | U14 VM bypass (CVM1) | (139.0, 107.527) | **7.13 mm** | 6.41 mm |
| **C32** | 0603 47 nF X7R 50 V (CL10B473KB8NNNC) | U14 CFLY (CPH-CPL) | (140.5, 110.277) | 7.50 mm | **7.40 mm** |
| **C50** | 0402 100 nF X7R 50 V (CL05B104KB54PNC) | U15 VM bypass | (95.5, 107.527) | **6.92 mm** | 6.18 mm |
| **C46** | 0603 47 nF X7R 50 V (CL10B473KB8NNNC) | U15 CFLY | (97.0, 110.277) | 7.26 mm | **7.15 mm** |

VM pin row of U14 is at global (133.100, 111.527 / 112.027 / 112.526) for pins 9/10/11 respectively, and CPH/CPL at (133.100, 110.527 / 110.027). VM pin row of U15 is at (89.850, 111.5-12.5).

These caps are 6-8 mm from the relevant device pins. TI's reference layout puts them within ~2 mm. At 6-8 mm the loop inductance to the VM pin is roughly 5-10 nH, which at fast switching transitions (8 A peak, ~50-200 V/µs slew) gives 0.4-2 V loop voltage, partially defeating the purpose of the high-frequency bypass.

**Note on the prior review's "C36 ... 3.4 mm from U14 centre" claim:** that number was distance to *EP center* (135.5, 110.277). TI's guidance is for distance to *device pins*, not EP. Re-stated correctly above.

**Action:** move C36, C32 next to U14 VM/CPH/CPL pins (≤2 mm from the pin row at x=133.1). Same for C50/C46 next to U15 (≤2 mm from x=89.85). This may require relocating the bulk cap cluster (C40/41/42 and C37/38/39) outward.

### C2 — DRV8316C EP via count vs. TI recommended layout (re-verifying the prior claim)

**Prior claim being re-verified:** "~22 thermal vias under each DRV8316 EP — well above the 9-12 spec."

**TI DRV8316C datasheet, page 83 sec 11.1 Layout Guidelines, full quote of relevant passage:**
> The device thermal pad should be soldered to the PCB top-layer ground plane. Multiple vias should be used to connect to a large bottom-layer ground plane. The use of large metal planes and multiple vias helps dissipate the I²×RDS(on) heat that is generated in the device.
>
> To improve thermal performance, maximize the ground area that is connected to the thermal pad ground across all possible layers of the PCB. Using thick copper pours can lower the junction-to-air thermal resistance and improve thermal dissipation from the die surface.

**The datasheet text does not give a numerical via count.** The "9-via minimum" or "9-12 spec" referenced in prior reviews is **not present in SLVSH07** — that number appears to have been confabulated or copied from a different TI part. The only quantitative guidance is the **Layout Example figure (sec 11.2, page 84)**, which I rendered and visually counted: TI's reference layout shows a **4 × 4 = 16-via array** under the EP.

**Actual via count under each EP** (parsed from .kicad_pcb, dedupe by XY, GND net only, within ±2.85 mm box of EP center):

| Driver | EP center | Unique GND via positions | Raw via count | Notes |
|---|---|---|---|---|
| U14 | (135.500, 110.277) | **18** | 18 | Clean. Exceeds the 16 in TI's example. |
| U15 | (92.250, 110.277) | **18** | 26 | 8 stacked duplicates — see B5. The unique-position count matches U14. |

Via specs: **0.45 mm pad / 0.30 mm drill**, F.Cu↔B.Cu through. Consistent with TI's "multiple vias" guidance.

**Verdict:** the *number* of unique vias (18 each) exceeds TI's reference example (16) and is acceptable. The 16 vs 18 difference is not material. The U15 stacked-via fault (B5) is the actual problem — it's a fab issue, not a thermal one.

**Correction to prior review:** drop the "9-via minimum" claim. Replace with: "TI's layout example (sec 11.2) uses a 4×4 array; Twinspora has 18 unique via positions per EP, exceeding TI's example."

### C3 — Twelve `starved_thermal` connections to GND zone

drc.json (re-verified, list unchanged from prior review):

- J5 pin 1 (CAN GND) at (140.050, 132.800)
- U9 pin 1 (LDO GND) at (85.050, 129.465)
- C23 pin 2 (114.839, 133.117)
- C8 pin 2 (87.000, 128.750) — 5 V deco
- C4 pin 1 (84.680, 128.200) — 5 V
- **X1 pin 2 (125.875, 119.650) and pin 4 (124.125, 121.850)** — crystal GND, clock-stability concern
- C60 pin 1 (98.480, 118.500) — 3.3 V deco at U18 encoder
- C14 pin 1 (129.475, 126.500)
- U7 pin 63 (121.311, 126.742) — STM32 VSS pad
- C59 pin 1 (137.780, 117.700) — 3.3 V near CAN
- R5 pin 2 (116.890, 101.600)

Zone min_spoke = 2; these have actual_spoke = 1. Single-spoke thermal relief has ~2× the thermal resistance and is mechanically weak on rework. STM32 VSS and crystal pins matter most.

**Action:** widen `thermal_bridge_width` (currently 0.5 mm) on the In1.GND zone, or hand-place a second GND via beside each affected pad to force the second spoke.

### C4 — H1 / H4 / H7 / H10 mounting-hole footprints generate 18 hole_clearance + 8 mask-bridge errors

Verified by reading the H1/H4/H7/H10 footprints (`MountingHole:MountingHole_3.2mm_M3_Pad_Via`) directly from kicad_pcb:

- Each has **9 thru-hole pads** (1 center + 8 stitching at 2.4 mm radius — kicad_pcb L23666-style pad listing). Pad type is `thru_hole` (not `via`); shape circle.
- The 8 stitching PTH pads have NPTH-of-Hxx (the stacked SMT standoff `Mechanical:SMD_BD5.6-D3.6` with 3.6 mm NPTH) within their hole-clearance window. Resulting DRC: at H10/H12 alone, 9 hole_clearance violations (one for the centre PTH-NPTH pair at 0.000 mm, plus 8 for the stitching pads at 0.100 mm). Total over H1/H4/H7/H10 = 18 hole_clearance + 4 holes_co_located + 4 npth_inside_courtyard + 8 solder_mask_bridge.

(Prior review said "33 hole-clearance" — current DRC shows 18; difference is because KiCad 10 reports `hole_to_hole` (33) and `hole_clearance` (18) as separate counts. Total mounting-related errors are still ~38 ignoring duplicates.)

**Action:** widen the stitching ring to ≥2.0 mm radius beyond the M3 hole edge so it doesn't conflict with the 3.6 mm standoff NPTH, or replace the 8 stitching PTH pads with a single GND pour + GND vias outside the standoff body.

### C5 — Eighteen courtyard overlaps in the central cluster (re-verified)

drc.json `courtyards_overlap` list (all 18 confirmed):

- C49/C48 (1.75 mm pitch, 0805) — same for C34/C35
- C28/C26, C27/C25 (the 4-cap diamond around U7 NW corner)
- R28/R21, R27/R21, R23/R24 — 0402 quartet collisions
- TP19/R12, TP21/R13, TP26/C5 — test points on top of resistors
- C8/C7 (1.86 mm pitch)
- C39/H10, C38/H10, C37/H10 — VCC bulk caps butted into the M3 hole
- U6/U19, U18/C60 — IC and adjacent decoupling cap touching
- C1/U19, R30/D3

Pick-and-place is OK; rework with a 2-3 mm conical iron tip will not fit.

### C6 — Two zombie tracks and one orphan TP (re-verified)

drc.json `track_dangling`:
- Track [/SPI2_MISO] on B.Cu, length 1.000e-06 mm at (100.840, 128.160)
- Track [/BOOT] on B.Cu, length 0.2982 mm at (131.640, 125.860)

drc.json `unconnected_items`: Pad 1 [/VCP] of TP46 at (103.473, 111.130) plus a 4 mm orphan /VCP F.Cu segment.

**Action:** delete all three.

### C7 — CAN-FD diff pair fragmented and length-mismatched

Re-verified by parsing all `(segment ... (net "X"))` blocks of the .kicad_pcb (1859 segments total):

| Net | F.Cu | In2.Cu | B.Cu | Total segments | Total length |
|---|---|---|---|---|---|
| /CAN_H | 32 | 11 | 19 | **62** | **123.88 mm** |
| /CAN_L | 22 | 6 | 14 | **42** | **112.37 mm** |

**11.51 mm length mismatch** between the two diff lines. At 5 Mbps CAN-FD that's roughly 60-80 ps of intra-pair skew (electrical length on FR4 ≈ 6-7 ps/mm), tolerable for the bit period but couples to common-mode noise and unbalances the receiver thresholds. Combined with the In2.Cu split-plane region under part of the route (see `04_pcb_inner.md` B-1, B-2), this is a real EMC liability.

**Action:** route CAN_H and CAN_L as a clean diff pair on a single layer (preferably F.Cu over solid In1.Cu GND), match lengths within 1 mm.

### C8 — USB D+/D- length mismatch ~2 mm, no impedance control

Re-verified:

| Net | F.Cu | In2.Cu | B.Cu | Total | Length |
|---|---|---|---|---|---|
| /D+ | 21 | 0 | 0 | 21 | **18.71 mm** |
| /D- | 20 | 0 | 0 | 20 | **20.67 mm** |

Both stay on F.Cu (good — In1.Cu solid GND is the reference plane below at 210 µm dielectric, per `04_pcb_inner.md`). Length mismatch ~1.95 mm, well within USB 2.0 FS tolerance (~5 mm). USB FS will work without controlled impedance.

`tuning_profiles` in twinspora.kicad_pro is unset — no impedance constraint defined. With 0.20 mm trace width on 0.21 mm prepreg er≈4.4 to In1.Cu, single-ended Z₀ is approximately 65-70 Ω; coupled differential Z_diff is approximately 90-100 Ω depending on gap (could not measure gap without rendering). This is acceptable for FS USB.

### C9 — Crystal X1 ~10 mm diagonal from STM32 OSC pins, plus 2 starved_thermal

X1 (X322512MSB4SI, 4-pad SMD crystal) at (125.0, 120.75), 90°. U7 STM32G473RB at (115.0, 125.028), -135° (LQFP-64 rotated 45°). Center-to-center distance ≈ 10.9 mm. OSC_IN/OSC_OUT trace length ~8-12 mm running across mid-board F.Cu zone fills.

Per ST AN4488 §3.3 (Clock System), the crystal should be placed close to the OSC pins. Twinspora is at the edge of typical guidance. Combined with the two starved_thermal connections on X1 pins 2 and 4 (see C3), the HSE oscillator is the most sensitive node on the design.

For a 12 MHz HSE this is functional but tight. Per master findings D3, the load caps (30 pF) match the X322512MSB4SI 20 pF datasheet load correctly. Verify visually on F.Cu: (a) OSC traces are guarded by GND on both sides, (b) load-cap returns connect with 2 GND vias right at the crystal, (c) no PHA*/PHB*/PHC* gate-drive nets cross within 2 mm.

### C10 — VCC bulk cap cluster overlaps H10 courtyard (re-verified)

drc.json: courtyards C39 / C38 / C37 each overlap H10. All three caps are at x=145.250 (102.65 / 104.64 / 106.60). H10 M3 mounting hole is at (150.057, 104.250). Combined with B1, the upper-right power-input region is over-packed.

**Action:** pull the right cluster ≥0.5 mm clear of H10.

---

## NITS

### N1 — Silkscreen pollution (199 silk_over_copper, 192 text_height, 118 silk_overlap, 31 silk_edge_clearance)

Visual inspection of `D:\gehub\twinspora\_review\exports\layers\F.Silkscreen.pdf` confirms the central area (around U7/X1/encoders) is essentially unreadable — refdes stack on top of pads and on each other. After placement is locked, hide refdes for parts smaller than 0805 in this region. Cosmetic.

### N2 — Footprint-symbol-mismatch warnings (46 lib_footprint_mismatch + 1 lib_footprint_issues)

Cosmetic. Set the footprint property in the symbol or right-click each footprint and "Update with override footprint".

### N3 — 16 padstack_invalid on H3/H6/H9/H12 corner pads

Custom pad shapes resolve to multiple polygons. Cosmetic; gerbers rasterize fine.

### N4 — F.Paste apertures

Visual inspection of `D:\gehub\twinspora\_review\exports\layers\F.Paste.svg`: the DRV8316 EP shows a single solid 5.7 × 5.7 mm aperture. For best yield TI typically recommends splitting the EP paste into a grid (typical 4×4 or 5×5 with ~50-70 % paste coverage) to prevent solder volcano + IC float during reflow.

> Note: this is **not** stated in DRV8316C SLVSH07 — it is general industry practice for QFN/VQFN with large EPs (e.g. IPC-7093). I am citing it as a process-level recommendation, not a TI requirement.

### N5 — F.Mask bridges (8) all under SMT standoffs

All 8 `solder_mask_bridge` errors map to the H1/H4/H7/H10 stack with their corresponding standoffs H3/H6/H9/H12. Same root cause as C4.

### N6 — Encoders U16 (135.0, 120.028) and U18 (95.0, 120.028) on F.Cu

Per master findings A2 #11, the encoders should be on B.Cu under the rotor magnets. This is a top-level design-intent issue and is logged there; not re-litigated here. Magnet-to-die spacing must include any standoff/lid clearance.

### N7 — VCC pour ampacity (cannot be fully verified without IPC-2152 source)

The prior review claimed "VCC pour ... provides adequate 8 A ampacity" citing IPC-2152. **I do not have the IPC-2152 PDF to quote directly**, and per the verification rules I cannot cite a third-party blog. I can only verify the geometry from the .kicad_pcb:

- VCC delivered via two zones on F.Cu (`VCC_F` priority 6, `VCC1` priority 7) plus one multi-layer pour on B.Cu+In2.Cu (`VCC_IN2` priority 8).
- Zone `min_thickness = 0.25 mm`; outer pour appears 3-5 mm wide visually in the F.Cu rendering between BK22 (J11/J12) and the bulk caps and DRV inputs (verified by reading the `(polygon (pts ...))` of `VCC_F` at kicad_pcb L65898).
- Phase nets PHA1/PHB1/PHC1/PHA2/PHB2/PHC2 are F.Cu pours (zones, not segments) with min_thickness = 0.25 mm.
- F.Cu = 35 µm (1 oz), confirmed in stackup.
- 0 motor-phase or VCC traces routed on inner copper (`segment` count for /PHx* nets = 0 across all layers; only zones).

**Without IPC-2152 quoted directly, I cannot independently restate the 8 A ampacity figure.** What I can confirm from the stackup and from `04_pcb_inner.md` (verified independently): VCC is also poured on B.Cu+In2.Cu, so total cross-section is roughly 1 oz F.Cu + 0.5 oz In2.Cu + 1 oz B.Cu in parallel where these pours overlap. For VCC current return through electrolyte the limiter is more likely the necks at via fields than the bulk pour. This is not a primary-source verifiable claim — flagged as **unverified**.

Per master findings D1, the binding limit is DRV8316C junction temperature (1.5-2 A RMS at 85 °C), not trace ampacity, so this is not a fab blocker even if IPC-2152 numbers were tighter than the prior review claimed.

### N8 — 25 F.Cu footprints have Reference text on B.SilkS (mirrored) — count corrected

Programmatic check on all 205 footprints: footprint primary `(layer "F.Cu")` AND its `Reference` property `(layer "B.SilkS")` with `(justify mirror)`:

```
R28, C51, U4, C40, C58, C44, C52, C39, C38, U5, C42, R27, R23, R24,
C56, C43, C41, C54, C57, LED1, R21, C37, C55, C53, R5
```

That's **25 footprints**, not 26+. The bottom silk will print component reference labels for parts that don't physically exist on the back side. Cosmetic but confusing in assembly.

**Correction to prior review:** count was 25, not "26+".

**Action:** in KiCad, select these and move Reference text back to F.SilkS.

### N9 — 13 holes_co_located (9 of these are the U15 stacked vias from B5)

Of the 13 `holes_co_located` errors:
- 9 are duplicate vias on U15 EP and one under U7 — actual fab errors (B5).
- 4 are the H1/H4/H7/H10 + standoff stacks — by-design (C4).

After fixing B5 the count drops to 4, all explained.

---

## Notes / positives

- **Edge.Cuts** — closed rectangle (76.525, 100.800) → (153.475, 137.725) with 3.4 mm rounded corners. No zero-length segments, no degenerate edges. Good.
- **C32/C46** = 47 nF X7R 50 V (CL10B473KB8NNNC, 0603) — matches DRV8316C datasheet sec 8.3 Table 8-1 CFLY exactly: "X5R or X7R, 47-nF". (Prior briefing of "22 nF" was wrong.)
- **C36/C50** = 100 nF X7R 50 V (CL05B104KB54PNC, 0402) — matches CVM1 in Table 8-1: "X5R or X7R, 0.1-µF". The cap values are correct; the placement is the issue (C1).
- **C40/C41/C42** = 10 µF X5R 50 V (GRM21BR61H106KE43L, 0805) — matches CVM2: "≥ 10-µF, voltage rating ≥ 2× operating (i.e. ≥ 48 V)". 50 V rating meets the spec.
- **C43/C57** = 330 µF SMD electrolytic plus C44/C58 = 330 µF radial THT — large bulk per sec 10.1 ("Bulk Capacitance"). Value fine; placement (B1) is the issue.
- **VM/charge-pump/AVDD** — TI Layout Example sec 11.2 page 84 visible in `drv8316c_p84_layout_zoom.png`: shows 4×4 = 16-via EP array, ceramics directly adjacent to package. Twinspora has 18 vias under each EP — exceeds the example.
- **In1.Cu = solid GND** (per `04_pcb_inner.md`) — textbook L2 placement, ideal F.Cu signal reference.
- **Component density** 37 (front) vs 9.6 (back) per stats.json — heavily front-loaded, but back has GND copper area 2614 mm² to share heat.
- **No motor-phase or VCC routed on inner copper** — keeps the high-current paths on 1 oz outer layers (smart given 0.5 oz inner copper).
- **Test points** (TP1-TP47) accessible on F.Cu, 1.0 mm SMD pads — fine for needle probes; some courtyard collisions (C5).

---

## Suggested fix order

1. **B5** — delete the 9 stacked duplicate vias (8 on U15 EP + 1 under U7). Single-edit fix that closes 9 DRC errors and prevents fab drilling failure.
2. **B1** — move C43, C57 inward by ≥1 mm (or rotate 90°).
3. **B4** — move U5 ≥0.4 mm interior.
4. **B3** — shift J5 / J1 ≥0.3 mm up.
5. **B2** — move GND via at (136.5, 101.95) or shift J9.
6. **C1** — move C36/C32/C50/C46 to within 2 mm of the relevant DRV8316 pins; relocate C40/41/42 outward to make room.
7. **C4** — widen the H1/H4/H7/H10 stitching ring to ≥2 mm beyond the standoff NPTH.
8. **C7** — re-route CAN-FD diff pair on F.Cu over solid In1.GND, length-match within 1 mm.
9. **C3** — widen `thermal_bridge_width` or hand-place 2nd GND vias on the 12 starved_thermal pads (priority X1 pins 2 & 4, then U7 pin 63).
10. **C6** — delete /SPI2_MISO zombie, /BOOT stub, /VCP orphan.
11. **C5, C10** — pull courtyard-overlapping clusters apart by ≥0.5 mm where rework matters.
12. **N8** — move the 25 mirrored Reference texts back to F.SilkS.
13. **N1** — silk polish: hide refdes for sub-0805 parts in the central cluster.

---

## Corrections to prior version

| Prior claim | Status | Correction |
|---|---|---|
| "~22 thermal vias under each DRV8316 EP — well above the 9-12 spec" | **Wrong (no such spec exists)** | TI SLVSH07 sec 11.1 says "Multiple vias should be used" with no number. Sec 11.2 Layout Example (page 84) shows a 4×4 = 16-via array. Actual unique-position count is 18 per EP, not 22 (raw count of 22 included the duplicates flagged in B5). U14 has 18 unique; U15 has 18 unique + 8 duplicates = 26 raw. |
| "C36 ... 3.4 mm from U14 centre" | **Misleading** | 3.4 mm was distance to EP center; distance to nearest VM pin is **7.13 mm**. Same applies to C50. Now flagged as CRITICAL C1. |
| "VCC pour ... provides adequate 8 A ampacity" (citing IPC-2152) | **Cannot independently verify** | IPC-2152 PDF not in `_review/datasheets/`. Geometry confirmed (zones on F.Cu, B.Cu, In2.Cu; min_thickness 0.25 mm). Flagged as N7 — unverified, but per master findings D1 the binding constraint is DRV8316 junction temperature, not VCC ampacity. |
| "26+ F.Cu footprints have Reference text on B.Silkscreen" | **Off by one** | Programmatic count = exactly **25**. Listed by designator in N8. |
| "33 hole-clearance errors at H1/H4/H7/H10" | **KiCad 10 split** | Current DRC reports 18 `hole_clearance` + 33 `hole_to_hole` + 4 `holes_co_located` + 4 `npth_inside_courtyard` for the same physical situation. Total mounting-related errors ≈ 38 (was reported as 33 in older KiCad). |
| 12 starved_thermal | Re-verified | List unchanged from prior review. |
| New finding: **B4 — U5 GND pad 0.165 mm from top edge** | Newly flagged | Not in prior review. Confirmed in drc.json `copper_edge_clearance`. |
| New finding: **B5 — 9 stacked vias (real fab error)** | Newly flagged | Prior review attributed all 13 `holes_co_located` to mounting holes; in fact 9 of them are duplicate `(via ...)` blocks on U15 EP and U7 — distinct fab-blocking issue. |
| New finding: **C1 — DRV8316C ceramic decoupling caps too far from VM/CPH/CPL pins** | Newly flagged | Prior review checked distance to EP center (3.4 mm) and called it "adequate". Distance to actual VM pins is 7+ mm — too far per TI sec 11.1. |
| New finding: **C8 — USB D+/D- length mismatch ~2 mm** | Numerically verified | Prior review said "Length-matching not verified numerically." Now measured: D+ = 18.71 mm, D- = 20.67 mm. Acceptable for USB FS. |
| Bulk-cap value verification | Confirmed | C36/C50 = 100 nF, C32/C46 = 47 nF, C40/41/42 = 10 µF, C43/57 = 330 µF SMD electrolytic, C44/58 = 330 µF radial THT. All match TI Table 8-1 recommendations. |

---

## Primary-source citations

- **TI DRV8316C datasheet SLVSH07 (Dec 2022)** — `D:\gehub\twinspora\_review\datasheets\DRV8316C_TI.pdf`:
  - Page 5 (Pin Functions table) — VM bypass cap requirement, CFLY 47 nF, CCP 1 µF, AVDD 1 µF.
  - Page 19 (sec 8.3, Table 8-1) — full external component list with values and ratings.
  - Page 83 (sec 11.1 Layout Guidelines) — quoted in C1 and C2.
  - Page 84 (sec 11.2 Layout Example) — visual 4×4 EP via grid; rendered to `D:\gehub\twinspora\_review\datasheets\drv8316c_p84_layout_zoom.png`.
  - Page 6 (sec 7.1, 7.3) — operating range 4.5-35 V, abs max 40 V.
- **ST AN4488** — referenced in C9 for crystal placement guidance. Not held locally; cited only qualitatively.
- **IPC-2152** — referenced by prior review for ampacity. **Not held locally**, so no numerical claim from this standard appears in this re-verified review (see N7).
