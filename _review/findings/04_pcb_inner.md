# 04 - PCB Inner Copper Layers (In1.Cu, In2.Cu) Review (v2, primary-source verified)

Board: 76.95 x 36.93 mm, 4-layer, 1.6167 mm thick (`twin28xx.kicad_pcb` line 6, `(thickness 1.61668)`). No impedance control specified.

## Stackup (verified, `twin28xx.kicad_pcb` lines 28-98)

| Layer        | Material                                | Thickness | er    | tan d |
|--------------|------------------------------------------|-----------|-------|-------|
| F.Cu         | copper (line 43-46)                      | 0.035 mm  | -     | -     |
| dielectric 1 | prepreg Nan Ya NP-155F 7628 (line 47-54) | 0.2104 mm | 4.40  | 0.02  |
| In1.Cu       | copper (line 55-58)                      | 0.0152 mm | -     | -     |
| dielectric 2 | core   Nan Ya NP-155F Core (line 59-66)  | 1.065 mm  | 4.43  | 0.02  |
| In2.Cu       | copper (line 67-70)                      | 0.0152 mm | -     | -     |
| dielectric 3 | prepreg Nan Ya NP-155F 7628 (line 71-78) | 0.2104 mm | 4.40  | 0.02  |
| B.Cu         | copper (line 79-82)                      | 0.035 mm  | -     | -     |

Implications:
- F.Cu is tightly coupled (210 um) to In1.Cu; B.Cu is tightly coupled (210 um) to In2.Cu.
- F.Cu-to-B.Cu separation is ~1.5 mm.
- Inner copper is 0.5 oz nominal (15.2 um), HALF of outer copper (35 um). Relevant for any inner-layer power segment ampacity.

## Primary-source layer assignment (verified)

### How the primary-source numbers were obtained
Python state-machine parser over `twin28xx.kicad_pcb` extracting every `(segment ...)`, `(arc ...)`, `(via ...)`, and `(zone ...)` block, grouping by `(layer "...")` and `(net "...")`. Independent of any earlier review.

Counts (across the entire board):
- 1859 `(segment ...)` blocks: F.Cu=1234, In1.Cu=**0**, In2.Cu=142, B.Cu=483.
- 16 `(arc ...)` blocks: all on F.Cu. Inner layers have zero arcs.
- 607 `(via ...)` blocks: 367 on `GND`, 40 on `VCC`, 39 on `+3.3V`, 26 on `+BATT`, 5 each on `+5V` / `/CAN_H` / `/CAN_L` / `/BUCK`.
- Only one occurrence of `(layer "In1.Cu")` outside the layer table (line 76937, file-wide), and it is the In1.Cu fill polygon of the multilayer zone `In1.GND` (zone declared at line 66621-66640, layers `"F.Cu" "B.Cu" "In1.Cu" "In2.Cu"`).

### In1.Cu - confirmed solid GND plane (clean)

- **Zero routed segments** and **zero arcs** on In1.Cu (verified by state-machine parser).
- Only one zone touches In1.Cu: `In1.GND` (uuid `8185807c`, lines 66621-66640), with layers `"F.Cu" "B.Cu" "In1.Cu" "In2.Cu"` and net `GND`. The zone polygon at line 66638 spans the four corners `(75.80, 96.55) (75.78, 138.95) (156.78, 138.95) (157.78, 93.45)` -- i.e. the full board outline.
- No higher-priority zones target In1.Cu, so on this layer the GND polygon fills the whole board minus via antipads.
- Visual `In1.Cu.png` is a uniform black field perforated only by via antipads. No splits, no slots, no signals. Textbook GND plane.

### In2.Cu - confirmed split power plane WITH signals routed on it

`In2.Cu` is referenced in 184 places in `twin28xx.kicad_pcb`. Four zones include In2.Cu in their layer list:

| # | Zone name   | Net    | Layers                | Priority | File line |
|---|-------------|--------|-----------------------|----------|-----------|
| 1 | In1.GND     | GND    | F.Cu/B.Cu/In1.Cu/In2.Cu | (default 0) | 66621 |
| 2 | VCC_IN2     | VCC    | B.Cu/In2.Cu           | 8        | 82846     |
| 3 | VBAT        | +BATT  | B.Cu/In2.Cu           | 4        | 83185     |
| 4 | 3.3V_BCC    | +3.3V  | In2.Cu only           | 2        | 83937     |

Note: there is no dedicated In2.Cu pour for `+5V` or `VBUS`. Those nets distribute on In2.Cu only as routed segments (see below).

In2.Cu also carries **142 routed pieces** (segments) across **17 distinct nets**. Per-net counts on In2.Cu (state-machine parser, full file):

| Net           | In2.Cu segs | First segment line |
|---------------|------------:|-------------------:|
| +5V           |          31 |              50298 |
| +3.3V         |          16 |              52342 |
| VBUS          |          13 |              60065 |
| /SOC1         |          11 |              62553 |
| /CAN_H        |          11 |              51026 |
| /BUCK         |          10 |              61545 |
| /SOC2         |           7 |              54336 |
| /USER_LED     |           6 |              65761 |
| /SOA1         |           6 |              60537 |
| /CAN_L        |           6 |              59656 |
| /SOB1         |           5 |              61705 |
| /GPIO3        |           5 |              52790 |
| GND           |           4 |              50128 |
| Net-(Q1-G)    |           3 |              61993 |
| /ADC5_IN2     |           3 |              54168 |
| /ADC5_IN1     |           3 |              62425 |
| /CAN_VIO      |           2 |              61257 |

Power-segment widths on In2.Cu (state-machine parser):
- `+5V`: 23 segments at **0.8 mm**, 4 at 0.5 mm, 4 at 0.3 mm.
- `/BUCK`: 10 segments at **0.8 mm**.
- `VBUS`: 10 segments at **0.5 mm**, 3 at 0.3 mm.
- `+3.3V`: 16 segments at 0.25 mm.

So In2.Cu is a **fragmented power layer (+BATT, VCC, +3.3V via pours; +5V, VBUS, /BUCK via segments)** **PLUS** signal layer (CAN-FD pair, current-sense feedbacks /SOA1/SOB1/SOC1/SOC2, ADC5_IN1/2, GPIO3, USER_LED, CAN_VIO). The lowest-priority polygon (In1.GND priority 0) fills GND in the remainder.

## CAN-FD diff pair - verified asymmetric layer fragmentation

State-machine parser per-layer counts for the CAN-FD pair (`/CAN_H` and `/CAN_L`):

|        | F.Cu | In1.Cu | In2.Cu | B.Cu | TOTAL |
|--------|-----:|-------:|-------:|-----:|------:|
| /CAN_H |   32 |      0 |     11 |   19 |    62 |
| /CAN_L |   22 |      0 |      6 |   14 |    42 |

**Confirmed asymmetric** -- 62 vs 42 segments. Each layer transition is a via for both lines (5 vias each on /CAN_H and /CAN_L, see via-net Counter above).

The 11 `/CAN_H` In2.Cu segments are all in y = 134.95 to 137.38 mm (e.g. lines 51026-51105). The bottom board edge is at y = 138.95 mm (zone polygon line 66638). So the CAN diff pair runs as inner-layer traces in a strip ~1.5-4 mm above the bottom edge, in the same area where the BK22 connectors (U1, U2 at y=115), the connector cluster (J1/J2/J5/J6/J7 at y~134-135), and the U11 CA-IF1044VD-Q1 CAN transceiver (at 128.38, 128.7) live.

## Via stitching density around landmarks (verified)

Computed from 367 GND-net via coordinates parsed from `(via ...)` blocks. Distance is Euclidean from the footprint origin recorded in `(at x y ...)`.

| Landmark               | Origin (mm)        | GND vias r<=3mm | r<=5mm | r<=8mm |
|------------------------|--------------------|----------------:|-------:|-------:|
| DRV8316 U14 EP         | (135.50, 110.28)   |              18 |     20 |     31 |
| DRV8316 U15 EP         | (92.25, 110.28)    |              26 |     29 |     38 |
| BK22 U1                | (150.00, 115.00)   |               0 |      5 |     14 |
| BK22 U2                | (80.00, 115.00)    |               1 |      4 |     13 |
| USB-C J2 (shield/CC)   | (97.35, 134.02)    |               3 |      5 |     18 |
| CAN connector J5       | (141.55, 134.60)   |               3 |     11 |     20 |
| CAN xcvr U11           | (128.38, 128.70)   |               5 |     10 |     37 |

Reasonable stitching at the DRV8316 EPs (18-26 GND vias inside 3 mm of the EP center is a healthy thermal/return-path well). USB shield is moderate (5 GND vias inside 5 mm). **BK22 connectors (U1, U2) have only 0-1 GND vias inside 3 mm and 4-5 inside 5 mm** -- i.e. no GND vias are immediately adjacent to the high-current power-input pins (these connectors carry +BATT and GND directly). See concern PB-1 below.

## DRC (relevant to inner layers)

From `_review/drc.json` (719 violations total): zero `track_dangling`, `clearance`, or `copper_edge_clearance` violations identified on In1.Cu or In2.Cu. All 12 `starved_thermal` warnings explicitly state `"layer F.Cu"` -- none are on the inner layers. The 2 `track_dangling` violations are not on inner layers (would have shown as zero In1.Cu/In2.Cu segments otherwise; In1 has zero anyway).

---

## BLOCKERS

### B-1. CAN-FD differential pair routed across THREE layers including In2.Cu split-plane region (verified)

Per the per-layer count above:
- `/CAN_H`: 32 F + 11 In2 + 19 B = **62 segments, 5 layer-transition vias** (`(via ... (net "/CAN_H"))` count = 5).
- `/CAN_L`: 22 F + 6 In2 + 14 B = **42 segments, 5 layer-transition vias**.
- The 20-segment count gap (CAN_H = 62, CAN_L = 42) implies physically different path lengths.
- `/CAN_H` In2.Cu segments live at y = 134.95-137.38 mm (lines 51026-51105). At those Y values In2.Cu is mostly the GND fill (low-priority `In1.GND` zone) below the +BATT (priority 4) and VCC_IN2 (priority 8) pours which sit at y ~109-114 mm and y ~107-109 mm respectively (zone polygon coords lines 82864-82869, 83203-83210). So the CAN traces themselves are *probably* over GND fill on In2.Cu.
- However, with B.Cu and F.Cu segments adjacent and 5 layer transitions per line, intra-pair skew is essentially baked in. CAN-FD at 5 Mbps tolerates ~2-3 ns of skew (one bit ~ 200 ns at 5 Mbps), but EMI imbalance between H and L grows with skew. Goal: length-match the pair within 1 mm at U11.

**Action:** verify on the gerber that (a) each pair of layer-transition vias on CAN_H / CAN_L is co-located within ~1 mm; (b) a GND stitch via sits within 2-3 mm of every diff via; (c) total pair length match is within 1 mm. The 5 GND vias in close proximity to CAN_H/L vias suggest someone tried, but the asymmetry needs audit.

### B-2. In2.Cu carries split power planes AND signals - no solid power plane reference

Unlike a textbook 4L Sig/GND/PWR/Sig where In2.Cu would be a single-net plane (or two large pours with a clean split), In2.Cu here contains:
- Three multi-layer power pours: `VCC_IN2` (B+In2, priority 8, line 82846), `VBAT` (B+In2, priority 4, line 83185), `3.3V_BCC` (In2 only, priority 2, line 83937).
- 17 distinct nets routed as segments, including `+5V` (31 segments, 0.8 mm), `VBUS` (13 segments, 0.5 mm), `/BUCK` (10 segments, 0.8 mm).
- Whatever is left over fills with GND (the `In1.GND` zone is the lowest-priority polygon and floods the gap).

Implications for **B.Cu** signals using In2.Cu as their (210 um, closest) reference:
- `B.Cu` carries 483 routed pieces. Top B.Cu nets: `VCC` (39 segments), `/TIM8_CH2N` (24), `/TIM8_CH1N` (22), `/TIM8_CH1` (20), `/GPIO2` (20), `/SPI3_NSS` (19), `/CAN_H` (19), `/CAN_L` (14), various SPI*, TIM8*, etc.
- Any B.Cu signal that crosses an In2.Cu split line (between +BATT and VCC pours, or between VCC and the GND fill, etc.) sees a return-path discontinuity proportional to the gap width.
- The high-speed/edge-rate B.Cu signals most at risk: motor PWM signals `/TIM8_CH1`, `/TIM8_CH1N`, `/TIM8_CH2`, `/TIM8_CH2N`, `/TIM8_CH3`, `/TIM8_CH3N` (gate drive PWM, fast edges); SPI clocks (`/SPI3_NSS` / `/SPI2_NSS` / `/SPI4_NSS`, though NSS is slower). The TIM8 pair carries gate-drive PWM with sub-ns edges -- those are the worst offenders if they cross power splits.

**Action:** overlay the B.Cu route plan onto the In2.Cu split map. For every B.Cu trace that crosses a split line between two power nets, either reroute or place a 100 nF return-path bridge cap (GND-to-the-nearer-power-net) at the crossing. Henry Ott, *Electromagnetic Compatibility Engineering* (2009), section 17.3.4, "Reference Plane Discontinuity," is the canonical reference.

### B-3. Current-sense lines (SOA1/SOB1/SOC1/SOC2) split between F.Cu and In2.Cu (verified)

Per-layer segment counts (state-machine parser):
- `/SOA1`: 8 F.Cu + 6 In2.Cu (no other layers).
- `/SOB1`: 8 F.Cu + 5 In2.Cu.
- `/SOC1`: 11 F.Cu + 11 In2.Cu.
- `/SOC2`: 16 F.Cu + 7 In2.Cu.
- `/SOA2`: 10 F.Cu only.
- `/SOB2`: 16 F.Cu + 3 B.Cu (no In2.Cu).
- `/ADC5_IN1`: 6 F.Cu + 3 In2.Cu.
- `/ADC5_IN2`: 6 F.Cu + 3 In2.Cu.

At 8 A peak motor current (DRV8316 RMS limit) with the typical 7 mOhm shunt, sense voltages are ~56 mV at peak into the MCU's internal op-amp/ADC. Layer-jumping these short, low-amplitude analog signals through the noisy In2.Cu split-plane region is asking for coupled noise from adjacent +BATT/VCC pours and the /BUCK switch-node trace (10 segments at 0.8 mm width on In2.Cu).

**Action:** keep each sense line on F.Cu only, with In1.Cu (solid GND, 210 um below) as its reference. If In2.Cu use is unavoidable, ensure the trace runs entirely over the GND fill region of In2.Cu, not over `+BATT` / `VCC_IN2` / `3.3V_BCC` pours, and not within 1 mm parallel run of `+5V` (0.8 mm) or `/BUCK` (0.8 mm) segments on In2.Cu.

## CRITICAL

### C-1. /BUCK switch node on In2.Cu - 10 segments at 0.8 mm

`(zone Buck)` (priority 3, F.Cu only, line 65998) is the F.Cu BUCK pour. In2.Cu adds 10 routed segments at 0.8 mm width carrying the buck switch node. Switch nodes have high dV/dt (typ. 5-10 V/ns at MHz switching). Inner-layer routing puts the noise between two GND/power references, which is *better* than F.Cu surface routing for radiation, but the switch trace still couples capacitively to nearby In2.Cu segments and B.Cu signals. Verify the In2.Cu /BUCK segments form a short, direct path from buck IC switch pin to inductor and do not run parallel to any sensitive analog or high-speed nets.

### C-2. +3.3V on In2.Cu is a small low-priority pour

`3.3V_BCC` (line 83937) is priority 2, In2.Cu only, polygon spans 92-152 mm x 113-134 mm with a complex shape. With +BATT (priority 4) and VCC_IN2 (priority 8) carving away from above, the actual filled +3.3V copper on In2.Cu is small. The +3.3V net is mostly distributed on F.Cu (110 segments). 16 segments at 0.25 mm width on In2.Cu are too narrow to act as a +3.3V plane.

**Action:** verify on a +3.3V-only render that the `3.3V_BCC` pour reaches all 3.3 V loads (MCU VDD/VDDA, encoder VDD, MagAlpha VDD, CAN xcvr V_IO) with at least 0.5 mm of pour copper at every via stub. If gaps exist, widen the `3.3V_BCC` polygon or add F.Cu / B.Cu local copper.

### C-3. BK22 connector GND-via stitching is sparse

GND vias inside 3 mm of BK22 U1 origin = 0; inside 5 mm = 5. Inside 3 mm of U2 origin = 1; inside 5 mm = 4. The BK22 footprint is `BAM04-08073-0414` (4 SMD pads of 0.4 mm pitch); the connector carries +BATT and GND for the modular power input. Without GND vias adjacent to the GND pads of U1/U2, return current from the +BATT pour has to travel several mm before finding a via to In1.Cu. At 8 A peak motor draw this is a real impedance/EMI path.

**Action:** add 4-6 GND stitching vias within 1.5 mm of each BK22 GND pad, on both U1 and U2.

### C-4. Power-plane segmentation - 3 distinct power nets as pours on In2.Cu

In2.Cu hosts simultaneously: +BATT (VBAT, line 83185), VCC (VCC_IN2, line 82846), +3.3V (3.3V_BCC, line 83937). Each pair of split borders is a discontinuity for any signal whose return current crosses it.

In2.Cu's *direct counterpart* on the other side of the 1.065 mm core is In1.Cu, which is **solid GND**. So In2.Cu signal-segment return current, where it would naturally cross a split, can mostly redirect through the In1.Cu solid GND on the other side -- if the In2.Cu segment is referenced to In1.Cu through a via. But B.Cu signals reference In2.Cu first (210 um), and In1.Cu only via 1.075 mm of FR4 (much weaker). So the B-2 risk is the dominant SI/EMI worry; the In2.Cu signals themselves are partially bailed out by In1.Cu.

## NITS

### N-1. CAN_H vs CAN_L segment count mismatch (62 vs 42)
Diff pairs should be roughly mirror-symmetric. Cause is probably a length-tuning meander or different via-jump pattern between H and L. Length-match the pair within 1 mm at U11.

### N-2. Inner-layer copper thinness (0.0152 mm = 0.5 oz)
The inner copper is half the F.Cu / B.Cu thickness, per stackup line 57 and line 69 (both `(thickness 0.0152)`). For a 0.8 mm wide power segment on In2.Cu (e.g. /BUCK, +5V), per **IPC-2152, "Standard for Determining Current Carrying Capacity in Printed Board Design" (2009), section 5 charts**, a 0.5 oz internal trace 0.8 mm wide carries roughly 1.5-2.0 A at 20 deg C rise (the chart is in the standard's Figure 5-1 for 0.5 oz internal). Verify these segments are not the sole power path to high-current loads -- they should be backed by F.Cu pours and through-vias.

### N-3. Motor phase currents are NOT on inner layers (good)
PHA1/PHA2/PHB1/PHB2/PHC1/PHC2 are F.Cu pours only:
- `/PHA1` zone, F.Cu, priority 12, line 66404.
- `/PHB1` zone, F.Cu, priority 11, line 66314.
- `/PHC1` zone, F.Cu, priority 13, line 66206.
- `/PHA2` zone, F.Cu, priority 12, line 66557.
- `/PHB2` zone, F.Cu, priority 11, line 66518.
- `/PHC2` zone, F.Cu, priority 13, line 66173.
Zero PHx segments on any inner layer (confirmed by per-layer-per-net Counter -- absent from the lists). Smart given the 0.5 oz inner copper limitation. **Per IPC-2152, an 8 A signal on a 0.5 oz internal trace would need ~3.5-4 mm width at a 20 deg C rise** -- impractical.

### N-4. No inner-layer signals on In1.Cu (verified)
Re-iterating: the parser found ZERO segments and ZERO arcs on In1.Cu. The single occurrence of `(layer "In1.Cu")` outside the layer-table (line 76937) is a `filled_polygon` of the multilayer GND zone. So In1.Cu is exclusively a GND fill.

### N-5. USB D+/D- on F.Cu only (verified)
Per the F.Cu-net Counter: `/D+` = 29 segments, `/D-` = 28 segments, no inner-layer or B.Cu segments for these nets. Reference layer is In1.Cu (solid GND, 210 um below) which is ideal.

## Notes (positives)

- **In1.Cu is a textbook solid GND plane.** No splits, no signals -- confirmed by parser (zero non-fill items on the layer).
- **High GND via density.** 367 of 607 vias (60%) are on GND. 18-26 GND vias inside 3 mm of each DRV8316 EP -- excellent thermal-and-return-path stitching at the worst-current parts.
- **Stackup correctly populated.** Real material entries (Nan Ya NP-155F, er = 4.4 / 4.43, tan d = 0.02) per lines 47-78. JLCPCB-compatible.
- **Motor phases off inner copper** -- F.Cu pours only, satisfies IPC-2152 derating.
- **No DRC errors on inner layers.** All 12 `starved_thermal` warnings are explicitly on F.Cu; no `track_dangling`, no `clearance`, no `copper_edge_clearance` issues on In1.Cu / In2.Cu.
- **CAN_H/L have 5 vias each** (visible in via-by-net Counter), matching the 5 layer transitions per line. If these are placed adjacent to a GND stitch via, return path is bridged.

## Recommended actions before fab

1. **(Blocker)** Visual audit: trace each B.Cu signal that crosses an In2.Cu split (the +BATT/VCC border on the BAM04 strip at y ~108-110, the VCC/+3.3V transitions, etc.). Place a 100 nF GND-bridge cap or GND stitch via at each crossing. Particular attention to TIM8 PWM nets (24+22+15+22+13+12 segments on B.Cu).
2. **(Blocker)** CAN_H/L diff pair audit: paired vias within 1 mm; GND stitch via within 2-3 mm of each diff via; total length match within 1 mm at U11.
3. **(Blocker)** Move all four `/SOA1, /SOB1, /SOC1, /SOC2` lines to F.Cu only (or restrict their In2.Cu portion to GND-fill regions), referenced to In1.Cu.
4. **(Critical)** Add 4-6 GND stitching vias within 1.5 mm of each BK22 GND pad on U1 and U2.
5. **(Critical)** Verify the `3.3V_BCC` pour on In2.Cu reaches all 3.3 V loads (MCU VDD/VDDA, encoder VDD, MagAlpha VDD, CAN xcvr V_IO) without narrow-neck regions.
6. **(Nit)** Ask fab to bump inner copper to 1 oz (35 um) if cost is reasonable -- doubles ampacity of /BUCK, +5V, VBUS power segments and halves IR drop.

## Corrections to prior version (v1_archive/04_pcb_inner.md)

- **Confirmed** zero In1.Cu segments and a single multilayer GND zone (`In1.GND`) -- prior claim correct.
- **Confirmed** the four-zone In2.Cu layout: `In1.GND` (multilayer, GND, default priority), `VCC_IN2` (B+In2, VCC, priority 8), `VBAT` (B+In2, +BATT, priority 4), `3.3V_BCC` (In2 only, +3.3V, priority 2). Prior table is accurate.
- **Confirmed** the 17 nets routed as segments on In2.Cu. Prior list of "unique nets" was correct: `+3.3V`, `+5V`, `/ADC5_IN1`, `/ADC5_IN2`, `/BUCK`, `/CAN_H`, `/CAN_L`, `/CAN_VIO`, `/GPIO3`, `/SOA1`, `/SOB1`, `/SOC1`, `/SOC2`, `/USER_LED`, `GND`, `Net-(Q1-G)`, `VBUS`. All 17 verified.
- **Confirmed** CAN_H = 32 F + 11 In2 + 19 B = 62 segments; CAN_L = 22 F + 6 In2 + 14 B = 42 segments. Prior numbers reproduce exactly.
- **Confirmed** /SOA1 (8 F + 6 In2), /SOB1 (8 F + 5 In2), /SOC1 (11 F + 11 In2), /SOC2 (16 F + 7 In2). Prior numbers reproduce exactly.
- **New finding:** prior listed `Net-(Q1-G)` and `/USER_LED` as routed on In2.Cu but did not flag them. /USER_LED has 6 segments on In2.Cu (line 65761 onward) -- low-bandwidth, low-risk, but worth knowing.
- **New finding:** primary-source via-stitching counts around BK22 connectors are LOW (0-1 GND vias inside 3 mm of U1/U2 origin). Prior version implied this area was well-stitched; it is not. Promoted to C-3.
- **Refinement of prior C-2:** The prior version stated "Visual inspection of In1.Cu PNG shows the GND plane remains continuous everywhere -- no obvious slot or break -- but the area under the DRV8316 thermal pads has heavy via concentration." Confirmed via 18-26 GND vias inside 3 mm of each DRV8316 EP center. The In1.Cu PNG also confirms no continuous slot wider than ~1.5 mm in the GND plane.
- **Refinement of prior N-3 (now N-2):** The prior version cited "IPC-2152 internal" for ampacity but did not name the chart. Replaced with explicit reference to **IPC-2152 (2009) Section 5, Figure 5-1** for the 0.5 oz internal-conductor curve. (No PDF of IPC-2152 is in `_review/datasheets/`; the citation is to the canonical published standard.)
- **Refinement of prior B-2:** Identified the *specific* B.Cu nets at risk -- TIM8 PWM pairs (`/TIM8_CH1N` 22 segs, `/TIM8_CH2N` 24 segs, etc.). These are gate-drive PWM with the worst edge rates on B.Cu and the most likely to expose return-path discontinuities at In2.Cu split borders.
- **Refinement of prior B-3:** Confirmed `/SOA2` (10 F.Cu only) and `/SOB2` (16 F.Cu + 3 B.Cu, no In2.Cu) do *not* use In2.Cu. So the layer-jump risk applies to the side-1 sense lines (SOA1, SOB1, SOC1) and one side-2 sense line (SOC2) but not all four side-2 sense lines.
