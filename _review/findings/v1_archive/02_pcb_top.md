# PCB Top-Side Review

Twinspora dual BLDC, 76.95 x 36.93 mm, 4-layer (F.Cu / In1.Cu / In2.Cu / B.Cu).
Stackup note: inner layers are 0.5 oz (0.0152 mm) — half the ampacity of outer 1 oz (0.035 mm).
Reviewed against `_review/exports/layers/{F.Cu,F.Silkscreen,F.Fab,F.Mask,F.Paste,F.Courtyard,Edge.Cuts}.{svg,pdf,png}`,
`_review/exports/3d/top.png`, `twinspora.kicad_pcb`, `_review/drc.json`.

## BLOCKERS

### B1 — Bulk electrolytic pads overhang the board edge (C43, C57)
Both 330 µF axial-style SMD electrolytics (`EEEFT1H331GP`, footprint `CAP-SMD_BD10.0-L10.3-W10.3-LS11.0-R-RD`) sit hard against the top edge:
- C43 at (109.000, 106.800), -90°. DRC: `Pad 2 [VCC] of C43` clearance to top Edge.Cuts (y=100.8) = **0.0000 mm** (lines 1286–1306 of drc.json).
- C57 at (123.700, 106.800), -90°. DRC: `Pad 2 [VCC] of C57` clearance to top Edge.Cuts = **0.0000 mm** (lines 1308–1329).

The 4.8 x 1.8 mm pads literally end on the route line. Any V-cut or router tolerance from the fab will cut into copper. Move both caps ~1.0 mm toward the board interior, or rotate 90° so the long axis is parallel to the edge. This is the biggest fab risk on the top side.

### B2 — VCC pad of J9 (motor terminal, +24 V) has 0.19 mm clearance to a GND via
At J9 pin-2 (`/PHB1`, x=135.750, y=103.149), a GND via at (136.500, 101.950) violates the 0.20 mm clearance rule (actual 0.1895 mm, lines 226–249). At 24 V this is fine electrically, but with ±10 % drill registration the GND via can short into the J9 PHB1 hole. Move the via at least 0.3 mm.

(The same area also generates the J9 silk_edge_clearance and J10/J9 footprint-symbol-mismatch warnings — they are cosmetic, not blocking.)

### B3 — J5/J1 pads less than 0.20 mm from the bottom Edge.Cuts
Bottom edge at y=137.725:
- `Pad 5 [GND] of J5` at (144.200, 136.400) — 0.175 mm to edge.
- `Pad 6 [GND] of J5` at (138.900, 136.400) — 0.175 mm to edge.
- `Pad 4 [GND] of J1` at (137.099, 136.529) — 0.196 mm.
- `Pad 5 [GND] of J1` at (132.498, 136.529) — 0.196 mm.

(drc.json lines 1170–1260). Same family of issue as B1 but for bottom side connectors. Move J5 (CAN SH1.0 4P at 141.55, 134.6) and J1 ~0.3 mm up. With a typical fab routing tolerance of ±0.15 mm, copper exposed at the board edge is a short-to-shield risk, and an ENIG/HASL deposit may bridge across the cut.

## CRITICAL

### C1 — Twelve `starved_thermal` connections to the GND plane
The multi-layer GND zone "In1.GND" (covers F.Cu / B.Cu / In1.Cu / In2.Cu, drc lines 1572–1845) feeds the following pads via only **1 spoke** when min-spoke = 2:
- J5 pin 1 (CAN GND), U9 pin 1 (LDO GND, SOT-23-3), C23 pin 2, C8 pin 2 (3.3 V deco), C4 pin 1 (5 V deco), X1 pins 2 and 4 (crystal GND), C60 pin 1 (3.3 V deco at U18 encoder VDD), C14 pin 1 (5 V), U7 pin 63 (STM32 GND/VDD pad), C59 pin 1 (3.3 V deco near CAN), R5 pin 2.

Single-spoke thermals are weaker mechanically (more pad lift on rework) and have ~2x the thermal resistance. For the STM32 VSS and crystal GND in particular this matters for clock stability. Either widen the thermal_bridge_width (currently 0.5 mm) or hand-place GND vias to give two spokes per pad.

### C2 — Crystal X1 is ~10 mm diagonally from STM32 OSC pins
X1 (X322512MSB4SI) at (125.0, 120.75), 90°; U7 (LQFP-64) at (115.0, 125.03), -135° (rotated 45°). Center-to-center ≈ 10.9 mm, so OSC_IN/OSC_OUT traces are 8–12 mm long and run across the F.Cu zone-fill mid-board. For a 24 MHz HSE this is functional, but combined with the starved thermal connections on X1 pin 2 and pin 4 (see C1) the crystal is the most exposed analog node on the design. Verify (a) traces are guarded by GND on both sides, (b) load-cap returns connect with two GND vias right next to the crystal, and (c) no high-dV/dt nets (PHA*/PHB*/PHC*) cross within 2 mm.

### C3 — Track [/SPI2_MISO] on B.Cu has length 1e-6 mm (numeric stub) at (100.84, 128.16)
DRC `track_dangling` (line 2032). A near-zero-length zombie segment that won't affect routing but shows up as an ERC error. Delete it. While there, also remove the 0.298 mm `/BOOT` stub on B.Cu at (131.64, 125.86), DRC line 2046.

### C4 — Unconnected /VCP test point and 4 mm dangling track
TP46 (Pad 1 [/VCP]) at (103.473, 111.130) is logically attached to /VCP but a separate 4.10 mm length of /VCP track on F.Cu (start (104.152, 110.352)) is not connected to anything — `unconnected_items` error (drc.json line 201). Either route the track to the TP46 pad or delete the orphan track.

### C5 — Eighteen courtyard overlaps make rework risky in the dense central zone
Notable pairs (drc.json 664–1168):
- C48 (98.25, 114.03) and C49 (96.50, 114.03) — 1.75 mm pitch on 0805; 0.75 mm courtyard intrusion. Same case for C34/C35.
- C25 (107.75, 121.78) / C26 (107.0, 121.03) / C27 (109.0, 120.53) / C28 (108.25, 119.78) form a tight 4-cap diamond around U7's NW corner; all four pairs report overlap.
- R23 (132.5, 130.875) / R24 (131.1, 130.9), R27/R28, R12/TP19, R13/TP21, R30/D3 — 0402s and test points on top of each other.
- C8 (87.0, 129.7) / C7 (88.86, 129.70) — 1.86 mm pitch.
- U6/U19 and U18/C60 — IC and decoupling cap touching.

None of these are DRC blockers individually, but cumulatively they prevent hand-rework with a 2–3 mm conical iron tip and they will fight automated optical inspection. If a board is meant to ever be hand-modified, give the top side at least 0.4 mm of courtyard headroom.

### C6 — H10 / H7 / H4 / H1 mounting-hole clusters generate 33 hole-clearance + 8 solder-mask-bridge errors
Each M3 mounting hole footprint (`MountingHole_3.2mm_M3_Pad_Via`, with 8 stitching vias around the perimeter) is co-located with a `Mechanical:SMD_BD5.6-D3.6` standoff (`SMTSOM225BTR`) at the same XY:
- H1+H3 at (80, 104.25)
- H10+H12 at (150.057, 104.25)
- H7+H9 at (150, 134.25)
- H4+H6 at (80, 134.25)

The DRC violations are: stitching-via PTH 0.5 mm drills lying inside the standoff's 3.6 mm NPTH (hole-to-hole 0.0 mm) and the standoff NPTH bridging the GND mounting-pad mask. This is by-design (stack the SMT standoff on the M3 hole), but the actual physical implementation will have eight 0.8 mm GND pads sitting under the standoff body. Two consequences:

1. The 0.5 mm stitching-via drills are inside the 3.6 mm clearance circle of the SMT standoff. The fab's routing/drilling tolerance can break the standoff seat. Either move the stitching via ring out to ≥2.0 mm radius from the M3 hole (the standoff lands on a ring of pads, not vias), or delete those eight vias and use a ground pour with a single GND via on the centre pad.
2. The exposed copper rings around the mount are masked from the standoff's NPTH; standoff solder paste will pull around the holes during reflow. Tent or NSMD the hole-stitching pads under the standoff foot.

### C7 — VCC bulk capacitor courtyard overlaps with H10
C39 (145.250, 102.647) and C38 (145.250, 104.635) overlap H10's courtyard (drc 825–869, 1124–1168). Combined with B1 (C43/C57 hanging off the top edge) the entire top right power-input region is over-packed. The VCC bulk is 9 caps in a 7.5 mm x 4.5 mm rectangle butted against H10 and the board edge. Recommend pulling the right-side cluster ≥0.5 mm clear of H10.

## NITS

### N1 — F.Silkscreen quality flags (199 silk_over_copper, 192 text_height, 118 silk_overlap, 31 silk_edge_clearance)
Looking at F.Silkscreen.png, the central area (around U7/X1/encoders) is essentially unreadable — the refdes are stacked on top of pads and on top of each other. Specific examples seen on the SVG:
- C26/C25/C27/C28 cluster has refdes overlapping pads.
- Polarity dots for C43/C57 are visible (good) but partly under the cap body.
- LED orientation marks (D3, LED2/3/4/5/6) — visible in F.Fab but the F.SilkS marks are clipped by adjacent pads.
- USR_LED button (SW1?), AS5048-style indicator dots for U18/U16 — fine.

This is a "polish later" issue. Once placement is locked, run "Auto-place silkscreen" or hide silkscreen for parts smaller than 0805. Most BOM-loaders won't read these tiny refs anyway, so the layout's optical inspection value is mostly cosmetic.

### N2 — Footprint-symbol-mismatch warnings (11)
The fiducials, mounting holes, J4/J6 pin sockets, J9/J10 Dorabo terminals, and BK22 connectors trip `lib_footprint_mismatch` because the schematic symbol doesn't carry the override footprint name. Cosmetic — nothing routes incorrectly. Either set the symbol footprint property in schematic or right-click each footprint and use "Update with override footprint".

### N3 — Padstack_invalid (16) on H9/H3/H12/H6 corner pads
Custom pad-shape on the standoff footprint resolves to multiple polygons. KiCad complains, fab tools rasterise correctly. Replace `(pad … custom)` with a polygonal pad whose shape is one connected region. Cosmetic.

### N4 — F.Paste apertures
Spot check vs F.Mask: 0805 pad pastes equal pad size (no shrink). For DRV8316 EP (5.7 x 5.7 mm) the F.Paste shows the EP solid (single square stencil opening). Recommend splitting the EP paste into a 3x3 or 4x4 grid with ~70 % paste coverage to prevent solder volcano + IC float. This is a stencil-only fix (modify the paste layer post-export, or edit the footprint pad to use multiple paste apertures). Not a DRC item.

### N5 — F.Mask bridges (8) all under SMT standoffs
The 8 `solder_mask_bridge` DRC errors all map to NPTH-of-Hxx vs PTH-1-of-Hyy, i.e. the same standoff/mountinghole stacking from C6. Once the standoff implementation is fixed these will disappear.

### N6 — Encoders U18, U16 are on the TOP layer
This is a deliberate choice (motor mounts on top, magnet diametrically polarised on the shaft above the chip). Just be aware: `stats.json front_component_density 37 vs back 9.6` is heavily front-biased; the back side is mostly GND pour. This concentrates heat from U7/U14/U15 and the LDOs all on F.Cu with limited copper ventilation around the encoders. Magnet-to-die spacing should be 1–2 mm including any standoff/lid. Mechanical clearance check needed against U2/U1 (BK22) which are 5.6 mm tall.

### N7 — Decoupling proximity check
Each VCC pin of U14 (DRV8316) has a 100 nF within ~3 mm: C36 (139.0, 107.5) is 3.4 mm from U14 centre (135.5, 110.27). U15 has C50 (95.5, 107.5) at 3.4 mm. STM32 (U7 at 115.0, 125.03) has C20, C21, C22, C24, C25, C26, C27, C28 all within 5–8 mm of the LQFP-64 ring — adequate, but check against the LQFP-64 power-pin map: there are 5 VDD pins distributed around the package and the cap cluster is concentrated on the NW side. PCB-side pin 12, 31, 47, 63, 64 (typical STM32G4 LQFP-64 VDD positions) should each get a cap within 3–5 mm. The east face VDD pins might be only served by C20 alone.

### N8 — USB D+/D- routing observation
J2 (USB-C) at (97.350, 134.017). STM32 at (115.0, 125.03). D+/D- nets routed on F.Cu, 0.2 mm width (from track-width census above). Trace length is the diagonal ~20 mm. For Full-Speed USB this is fine; differential 90 Ω with no impedance control is approximate but workable. Visually on F.Cu the pair tracks together, no obvious stubs. Length-matching not verified numerically.

### N9 — CAN-FD path
J5 (SH1.0 4P at 141.55, 134.6) → U13 (PESD2CAN ESD, SOT-23-3 at unknown coords) → U12 (ACT1210D CMC at unknown coords) → U11 (TCAN, DFN-8 at unknown coords) → STM32. Without doing the full trace I can confirm the layout direction looks linear (no loops in F.Cu). The CAN_H net is routed at 0.3 mm on both F.Cu and B.Cu — fine for 5 Mbps.

### N10 — TP46 floating
Mentioned in C4. Probably a stale test point from a removed VCP probe net.

## Notes

- **Total DRC count**: 1 clearance, 33 hole_clearance, 7 copper_edge_clearance, 18 courtyards_overlap, 4 npth_inside_courtyard, 8 solder_mask_bridge, 12 starved_thermal, 16 padstack_invalid, 13 holes_co_located, 2 track_dangling, 1 unconnected_items, plus 31 silk_edge / 199 silk_over_copper / 118 silk_overlap / 192 text_height / 11 lib_footprint_mismatch / 1 lib_footprint_issues / 46 lib_footprint_mismatch (cosmetic).
- **Edge.Cuts**: closed, single rounded rectangle (76.525,100.8) → (153.475,137.725) with 3.4 mm radius corners. No zero-length segments. Good.
- **Stackup**: 1 oz F.Cu/B.Cu, 0.5 oz In1/In2 — typical JLCPCB 4-layer. Watch inner-layer ampacity for VCC_IN2 (split B.Cu/In2.Cu pour for VCC).
- **Min track**: 0.16 mm; min via drill: 0.30 mm — both within JLCPCB 4-layer Standard.
- **Component density**: 37 / 9.6 (front / back). Typical for top-stacked-motor design.
- **Front copper area**: 2751 mm² of 2831 mm² board → 97 % copper fill on F.Cu.
- **Back copper area**: 2614 mm² → ~92 % fill on B.Cu (mostly GND).
- **Power scheme**: VCC (24 V) routed as F.Cu pour `VCC_F` + `VCC1` + B.Cu/In2 pour `VCC_IN2`. Phase nets PHA1/PHB1/PHC1/PHA2/PHB2/PHC2 each have F.Cu pour (`PHA1`...`PHC2`). Min-thickness 0.25 mm. With 2 layers (F.Cu 1 oz + In2 0.5 oz) carrying VCC, total ampacity for VCC is roughly equivalent to 1.5 oz of single-layer copper — adequate for 8 A peak if the F.Cu zone reaches at least 2 mm width all the way from BK22 to the bulk caps. Visually that looks satisfied.
- **Thermal vias under DRV8316 EPs**: counted ~22 vias under U14 EP and ~22 under U15 EP. Well above the 9-via minimum.
- **Mechanical**: 4 M3 mounting holes at corners + 4 SMT standoffs co-located. See C6.
- **Test points**: Many TPs (TP1–TP47 visible). Most are 1.0 mm SMD pads on F.Cu — fine for needle probes. Several courtyard-overlap with adjacent components (TP19/R12, TP21/R13, TP26/C5).

## Suggested fix order
1. Move C43, C57 inward by 1 mm (B1).
2. Reroute or move J5 / J1 by 0.3 mm to clear bottom edge (B3).
3. Move GND via at (136.5, 101.95) or shift J9 (B2).
4. Replace H1/H4/H7/H10 stitching-via ring with a wider ring (radius ≥ 2.0 mm) so it doesn't conflict with the SMT standoff NPTH (C6). This also kills the 8 mask-bridge errors and 33 hole-clearance errors in one go.
5. Increase thermal-bridge width on the GND zone or hand-place 2 spokes per affected pad (C1).
6. Delete `/SPI2_MISO` zombie segment, `/BOOT` stub, and the `/VCP` orphan track (C3, C4).
7. Move courtyard-overlapping passive clusters apart by ≥0.5 mm where rework matters (C5, C7).
8. Polish silk: hide refdes for parts smaller than 0805 in the central cluster (N1).
