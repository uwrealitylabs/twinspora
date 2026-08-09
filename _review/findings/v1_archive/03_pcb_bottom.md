# PCB Bottom-Side Pre-Fab Review — `twin28xx.kicad_pcb`

Reviewed: 2026-05-05
Source: `D:\gehub\twin28xx\twin28xx\twin28xx.kicad_pcb`
Stats: 76.95 mm × 36.93 mm, 4-layer, 1.62 mm thick.
Per `stats.json`: front-density 37.04%, back-density 9.59%, but **0 components** are recorded as residing on the back layer (`components.smd.back = 0`, `components.tht.back = 0`, `components.unspecified.back = 0`).

---

## BLOCKERS

### B1 — MT6701 magnetic encoders are placed on the WRONG side of the board (F.Cu instead of B.Cu)

The README explicitly states: *"Sized to fit two iPOWER GM2804 / Cubemars GL-30 motors **on the back of the PCB**."* The motor's diametric magnet sits below the PCB on the rotor shaft. The MT6701 must therefore face the magnet — i.e. it must be on **B.Cu** (bottom layer).

What the file actually shows:

| Designator | Footprint | Layer | Center (mm) |
|------------|-----------|-------|-------------|
| U18 | `Package_DFN_QFN:QFN-16-1EP_3x3mm_P0.5mm_EP1.7x1.7mm` | **F.Cu** | (95.0000, 120.0275) |
| U16 | `Package_DFN_QFN:QFN-16-1EP_3x3mm_P0.5mm_EP1.7x1.7mm` | **F.Cu** | (135.0000, 120.0275) |

Evidence:
- `twin28xx.kicad_pcb` line 6618–6619: `(footprint "Package_DFN_QFN:QFN-16-1EP_3x3mm_P0.5mm_EP1.7x1.7mm" (layer "F.Cu") … (at 95.000001 120.0275))` — Reference U18 at line 6624.
- `twin28xx.kicad_pcb` line 13129–13130: same for U16 at (135, 120.0275).
- All pads of U18 and U16 are on `"F.Cu" "F.Mask" "F.Paste"` (e.g. lines 7030–7195 for U18). Silk, courtyard, and fab marks are on `F.SilkS`/`F.CrtYd`/`F.Fab`.
- Independently confirmed by `stats.json`: `components.smd.back = 0`. Bottom-side B.Paste, B.Courtyard, B.Fab SVG exports contain only the board outline + drilled-pad apertures — **no SMD pads at all on the bottom**.

Consequences if fabricated as-is:
- Magnet → encoder die distance is now FR4 (1.62 mm) + QFN-16 package thickness (~0.85 mm) ≈ 2.5 mm. MT6701 datasheet operating range is ~1–3 mm but signal magnitude (and therefore angular noise) degrades sharply past ~2 mm. There is no mechanical way to compensate post-fab without reworking the board.
- The motor body's mounting fasteners go into the M3 corner holes (H1, H4, H7, H10) at z = (80/150, 104.25/134.25); the motor face is then directly behind/below the PCB. With encoders on the front, the magnetic-sense path passes through the **entire PCB stackup including all four copper layers and any GND/Power planes on those layers**.

### B2 — Continuous GND copper pour passes directly under both magnetic encoder sense paths

Zone `In1.GND` (line 66621) is filled on **F.Cu, B.Cu, In1.Cu, In2.Cu** with polygon outline (75.8, 96.55) → (157.8, 138.95), i.e. the entire board — and **no keepout/anti-pad** is defined under the MT6701 die. Confirmed by inspection of filled polygons: `In1.GND` filled polygons include vertices within 2 mm of both (95, 120.03) and (135, 120.03) on B.Cu (and also on inner layers).

Even if the encoders are moved to B.Cu (B1), the magnetic field will pass through the inner-layer GND pours and through the ~1.6 mm of FR4 with embedded copper, attenuating the field and producing eddy-current distortion. Standard practice for MT6701/AS5048 designs is a **circular copper keepout** of at least 5–6 mm diameter centered on the encoder die, on every layer beneath the magnet sensing path.

### B3 — Bottom-layer signal traces routed directly through the encoder magnetic-sense region

With encoders on F.Cu and copper underneath them, switching signals on B.Cu directly under the encoder will couple noise into the Hall bridges. Tracks routed within ±2.5 mm of U18 center (95.0, 120.03) on B.Cu include:

| Net | Width | Approx. position |
|-----|-------|-----|
| `/TIM8_CH2` (PWM) | 0.20 | (95.6, 121.5) → (93.2, 119.1) — *crosses directly over die* |
| `/TIM8_CH3` (PWM) | 0.20 | (92.9, 120.5) → (95.3, 122.9) — *crosses directly over die* |
| `/TIM8_CH3N` (PWM) | 0.20 | (91.5, 118.0) → (97.1, 118.0) |
| `/SPI1_MISO` | 0.16 | (93.25, 117.41) → (97.41, 117.41) |

The PWM gate-drive signals (`TIM8_CHx`) switch hard at the motor PWM frequency (typically 20 kHz–100 kHz) with fast edges — capacitive coupling into the encoder substrate is a real risk even before mechanical issues are addressed.

---

## CRITICAL

### C1 — No motor shaft cutout / clearance hole in `Edge.Cuts`

`Edge.Cuts` contains only the rectangular board outline (rounded corners at radius 3.4 mm) and **no interior cutouts/holes**. Verified by `Edge.Cuts.svg` and direct grep of `gr_arc`/`gr_circle`/`gr_line` in `Edge.Cuts` layer (the only `gr_circle` shapes in the design are 1 mm marker rings on `B.SilkS` at the encoder centers — line 45454 and 45465 — not Edge.Cuts).

Implications:
- For a motor like the GM2804 / GL-30, the shaft pokes axially out of the rotor by ~2–4 mm. With no cutout, the shaft will collide with the PCB face. Either the motor cannot be mounted, or the design relies on a custom shorter shaft, or there is an as-yet-unspecified mechanical spacer/standoff stack high enough to clear the shaft (in which case the M3 mounting screws in H1/H4/H7/H10 must be long enough — confirm assembly stack-up).
- Even if the shaft itself clears via a shortened shaft, the magnet on the rotor end-face needs ≤2 mm air gap to the encoder. Either a cutout in the PCB is needed under the magnet or the rotor must be set very close to the bottom face.

Verify mechanical drawing for the chosen motor revision and add a circular cutout (typically 6–10 mm diameter) centered on each encoder if shaft clearance is required.

### C2 — Motor-mounting hole pattern: M3 corners + M2 inner-row, double-stacked with SMD spacers

Mounting holes (`MountingHole_*` footprints, all on F.Cu):

| Designator | Type | Position (mm) |
|-----|-----|-----|
| H1 | M3 PTH 3.2 mm + Pad/Via | (80.0, 104.25) |
| H4 | M3 PTH 3.2 mm + Pad/Via | (80.0, 134.25) |
| H7 | M3 PTH 3.2 mm + Pad/Via | (150.0, 134.25) |
| H10 | M3 PTH 3.2 mm + Pad/Via | (150.057, 104.25) — **note 0.057 mm asymmetry** |
| H8 | M2 DIN965 Pad | (80.0, 110.0) |
| H11 | M2 DIN965 Pad | (80.0, 120.0) |
| H2 | M2 DIN965 Pad | (150.0, 110.0) |
| H5 | M2 DIN965 Pad | (150.0, 120.1) — **0.1 mm offset from H8/H11/H2** |
| H3, H6, H9, H12 | SMD standoff (`Mechanical:SMD_BD5.6-D3.6`, `SMTSOM225BTR`) | concentric with H1/H4/H7/H10 |

These SMD standoffs sit directly on top of the M3 PTH pads — `kicad-drc` flags 33 hole-to-hole, 18 hole-clearance, and 8 solder-mask-bridge errors due to this stack-up. This is intentional design (standoffs on top of M3 mounting pads) but the fabricator may flag the DRC errors. Confirm acceptance with the assembly house OR document the waivers.

The H10 X-offset (150.057 vs 150.000) and H5 Y-offset (120.1 vs 120.0) are inconsistencies that are likely not intentional and break the perfect rectangular mounting pattern by 50–100 µm. Tighten to round numbers.

### C3 — Bottom silkscreen labels for FRONT components (will print but reference no real parts on the back)

Multiple components mounted on F.Cu have their `Reference` text property forced onto `B.SilkS` with `(justify mirror)`. These labels will be silkscreened on the *bottom* face of the board, but the components themselves are on the *top*. This means anyone looking at the back of the manufactured PCB will see labels (R28, R23, R24, R21, C40–C42, C53–C58, C37–C39, C43, C44, C51–C56, U4, U5, R5, R27, LED1, …) without corresponding parts.

Examples:
- C40 footprint at line 3302–3303 is on F.Cu, but its Reference text (line 3308–3318) is on `B.SilkS`. Same for: C37, C38, C39, C40, C41, C42, C43, C44, C51, C52, C53, C54, C55, C56, C57, C58, R21, R23, R24, R27, R28, R5, U4, U5, LED1.

Either the components are intended to be moved to the back (no — pads are on F.Cu) or the labels were authored incorrectly. The likely root cause: design imported with a "back-side feel" labelling convention that didn't move the actual footprints to B.Cu. **Fix**: either move these footprints to B.Cu (correct intent for a "back-mounted motor" design — see B1) OR move the silk references back to `F.SilkS` so the labels match where parts are.

### C4 — Bottom layer carries hard-switching motor PWM gate-drive signals (separate from B3's encoder concern)

Beyond the encoder area, `TIM1_CHx` and `TIM8_CHx` (gate-drive PWM signals between MCU and DRV8316) and `SPIx_*` lines are routed substantially on B.Cu at 0.16–0.20 mm widths. Total B.Cu segment counts:

```
0.16 mm :  212
0.20 mm :  168
0.25 mm :    3
0.30 mm :   90
0.80 mm :   10  (mostly /5V_BKOUT and /BUCK)
```

Because the GND pour is interrupted by these traces on B.Cu, return-current paths for high-current motor phase loops on the inner planes have to detour around B.Cu trace routing. Verify return-current path integrity for /PHA1, /PHB1, /PHC1, /PHA2, /PHB2, /PHC2 (these are routed as zones, not segments — In2.Cu carries +BATT and VCC zones, In1.GND on F.Cu / B.Cu / In1.Cu / In2.Cu).

### C5 — DRC: 84 errors / 635 warnings — 1 unresolved unconnected, 7 copper-edge-clearance, 1 generic clearance violation

From `_review/drc.json`:

- **Unconnected (error, 1)**: `Pad 1 [/VCP] of TP46` at (103.47, 111.13) on F.Cu and a 4.10 mm dangling track. Test point intentionally left floating? Or missed connection? Verify intent.
- **Clearance (error, 1)**: 0.1895 mm (constraint 0.2 mm) between a F.Cu/B.Cu via and PTH pad 2 [/PHB1] of J9. Borderline — fab may still build but fix.
- **Copper-edge clearance (error, 7)**: 0.175 mm vs 0.2 mm constraint — affects J5 pads 5/6 [GND], J1 pads 4/5 [GND], U5 pad 2 [GND], C43 pad 2 [VCC], C57 pad 2 [VCC]. Most fabs tolerate 0.15 mm but this cuts margin to copper-burr-from-edge-routing. Pull these pads in 0.05 mm.
- **Solder-mask bridge (error, 8)**, **hole-clearance (error, 18)**, **hole-to-hole (error, 33)**, **padstack-invalid (error, 16)**, **NPTH-inside-courtyard (error, 4)** — all caused by H3/H6/H9/H12 SMD standoffs being placed concentrically over H1/H4/H7/H10 M3 PTH mounting pads. Likely intentional but DRC is warning that the stack is geometrically merging two electrically-different items — confirm with assembler that the standoffs solder onto the M3 pad ring as a single contiguous GND landing.
- **Starved thermal (error, 12)**: GND zone has only 1 spoke into J5/U9/C23/C8/C4/X1/C60/C14/U7/C59/R5 instead of the configured min 2. Increases thermal resistance / can lift pad during reflow under wave/IR profile. Re-cast spokes or relax min-spoke to 1.
- **courtyards_overlap (error, 18)**: e.g. R28/R21 — placement is dense; verify hand assembly is feasible.

---

## NITS / Style

- **N1** — `B.Fab` and `B.Courtyard` SVG exports are empty (only board outline and drill apertures). Consistent with no back-side parts. Sanity-check after the encoder relocation (B1) — these layers should populate when encoders move.
- **N2** — `H10` X is 150.057 mm (line 29367) instead of 150.000. `H5` Y is 120.1 mm (line 27191) instead of 120.0 (vs. H8/H11 at exactly 110/120). Tighten to a regular grid.
- **N3** — Reference designator text size 0.6 × 0.8 mm with 0.15 mm thickness is below KiCad's default-text-height-warning threshold (`text_height` warning fires 192 times in DRC). For 1 oz silk screen on most fabs this is the floor — readable but small. Consider 0.8 × 0.8 / 0.15 if space allows (low priority).
- **N4** — `silk_over_copper` fires 199× and `silk_overlap` 118× — expected on dense layouts but visually cluttered.
- **N5** — `lib_footprint_mismatch` fires 46× — non-blocking but suggests the footprint library is drifting from the central library. Run "Update footprints from library" before final tape-out.
- **N6** — `track_dangling` (warning) fires 2× — likely related to the floating /VCP test point. Clean these up.
- **N7** — `B.SilkS` `gr_circle` (lines 45454, 45465) are 1 mm-radius marker rings centered on the encoder die. Useful as a magnet-alignment target during assembly *if* the encoders move to B.Cu (B1). Currently they decorate the *bottom* of a board whose encoders are on top — keep them and they will become correct after B1.

---

## Notes / Confirmations

- Edge.Cuts: outer board outline only, 76.95 × 36.925 mm with rounded corners (R = 3.4 mm). No interior cut-outs (see C1).
- USB-C connector (J2) is reflow SMT (`USB-C_SMD-TYPE-C-31-M-12_1`), not recessed or board-edge mounted via mechanical cut-out.
- `B.Mask` SVG: only mask openings around through-hole and PTH pads (mounting holes, BK22 connectors, J9/J10 power terminals, USB shield etc.). No fine-pitch back-side mask apertures because there are no back-side fine-pitch parts. Once encoders are moved to B.Cu (B1), revisit B.Mask for solder-mask-bridge between the QFN's 0.5 mm-pitch pins and the EP.
- `B.Paste` SVG: empty save for QFN/SMD apertures around PTH/connector pads (which is wrong — those should NOT be on paste). The current `B.Paste` is therefore the apertures from F-side parts that have somehow leaked through; since there are no actual back parts, the back stencil should be empty. Re-export and verify after B1.
- Drill table (from `stats.json`): 520 vias @ 0.30 mm, 87 vias @ 0.40 mm, 32 PTH pads @ 0.50 mm, 8 @ 1.0 mm, 6 @ 1.4 mm, 4 PTH @ 3.2 mm (mounting holes M3), 4 NPTH @ 3.8 mm (likely the SMD standoff alignment NPTHs), 2 NPTH 0.75 mm. Min drill = 0.30 mm. Min track width = 0.16 mm. Min track clearance = 0.20 mm. All within JLC/Sierra/MacroFab default capability.
- 4 fiducials FID1/FID2/FID3 (+1 implied) are present — good for assembly.
- BOM lists C44, C58 as `50PX330MEFC10X16` THT bulk caps (10 mm body, 5 mm pitch) and C43, C57 as `EEEFT1H331GP` SMD bulk caps — these are the two large circles in the top render.
