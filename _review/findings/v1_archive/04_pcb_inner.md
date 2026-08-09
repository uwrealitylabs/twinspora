# 04 — PCB Inner Copper Layers (In1.Cu, In2.Cu) Review

Pre-fab review of the two inner copper layers of the 4-layer Twin28xx PCB.
Board: 76.95 x 36.93 mm, 1.62 mm. Stackup (per `(stackup ...)` in `.kicad_pcb`):

```
F.Cu   (35 um)
prepreg (210 um, NP-155F 7628, er 4.4)
In1.Cu  (15 um)
core    (1065 um, NP-155F core, er 4.43)
In2.Cu  (15 um)
prepreg (210 um, er 4.4)
B.Cu   (35 um)
```

So F.Cu is tightly coupled to In1.Cu (210 um), and B.Cu is tightly coupled to In2.Cu (210 um). F-to-B is ~1.5 mm apart.

## Layer assignment summary

### In1.Cu — Solid GND plane (clean)
- **Zero routed segments** on In1.Cu (`grep -c '(layer "In1.Cu")'` on segments = 0). The only `(layer "In1.Cu")` reference in the entire `.kicad_pcb` is from a `filled_polygon` belonging to the multilayer GND zone `In1.GND` (uuid 8185807c, layers F.Cu/B.Cu/In1.Cu/In2.Cu, net GND).
- No higher-priority zones target In1.Cu, so on this layer the GND polygon fills the whole board.
- Visual SVG/PNG confirms a near-100% solid black (filled) plane, perforated only by via antipads (lots of them: 607 through-vias board-wide, of which 367 are on GND).
- **This is the textbook role of the second layer in a Sig/GND/PWR/Sig 4L stackup.** Excellent.

### In2.Cu — Split power plane WITH signals routed on it
In2.Cu has 184 `(layer "In2.Cu")` items: a mix of zone fills, signal segments, and power segments. Zones with `In2.Cu` in their layer list:

| Zone name      | Net    | Layers              | Priority |
|----------------|--------|---------------------|----------|
| In1.GND        | GND    | F+B+In1+In2 (multilayer) | (default 0) |
| VCC_IN2        | VCC    | B+In2               | 8 |
| VBAT           | +BATT  | B+In2               | 4 |
| 3.3V_BCC       | +3.3V  | In2 only            | 2 |

Plus signal/power segments routed directly on In2.Cu (unique nets):
`+3.3V`, `+5V`, `/ADC5_IN1`, `/ADC5_IN2`, `/BUCK`, `/CAN_H`, `/CAN_L`, `/CAN_VIO`, `/GPIO3`, `/SOA1`, `/SOB1`, `/SOC1`, `/SOC2`, `/USER_LED`, `GND`, `Net-(Q1-G)`, `VBUS`.

So In2.Cu is a fragmented power plane (24V/+BATT, VCC, +5V, +3.3V, VBUS) PLUS signal layer (CAN-FD pair, current-sense feedbacks, I/O). The remainder (lowest-priority polygon) is GND.

## BLOCKERS

### B-1. CAN-FD differential pair routed across THREE layers including In2.Cu split-plane region
`/CAN_H` segments are split: 32 on F.Cu, 11 on In2.Cu, 19 on B.Cu.
`/CAN_L` segments are split: 22 on F.Cu, 6 on In2.Cu, 14 on B.Cu.
- Each layer transition needs a via on each of the two diff lines, ideally adjacent. Verify via positions for CAN_H vs CAN_L are paired (same X within ~1 mm, same layer transition). 5 GND vias on CAN_H/L are listed in via stats — should be CAN-stitch vias placed next to the diff vias to maintain return path.
- **Asymmetry of segment counts (CAN_H: 32+11+19=62 vs CAN_L: 22+6+14=42) implies physically different path lengths.** At 5 Mbps CAN-FD this is mostly tolerable but causes intra-pair skew + EMI imbalance. Goal: diff pair total length match within ~1 mm.
- The In2.Cu segments of CAN_H/L sit at y ~134-137 mm (near the bottom edge connector). On In2.Cu this region is a busy split-plane zone; CAN return-current path on B.Cu (closest reference for In2.Cu signals) may cross VCC/VBAT/+3.3V split lines. **Open the board and verify B.Cu under the CAN traces is unbroken GND** — if not, this is a return-path discontinuity blocker.

### B-2. In2.Cu carries split power planes AND signals — no solid power plane reference
Unlike a textbook 4L Sig/GND/PWR/Sig where In2.Cu would be a single-net plane (or two large pours with a clean split), In2.Cu here is a fragmented mix of {+BATT, VCC, +5V, +3.3V, VBUS, GND fill} pours plus segment-routed signals. Implications:
- **B.Cu signals using In2.Cu as their (closest, 210 um) reference will see split-plane discontinuities** wherever a B.Cu trace crosses from the +BATT region into VCC region, etc. Any B.Cu signal that crosses these split lines without a return-path bridge cap is an EMC/SI risk.
- Action: overlay B.Cu route plan onto In2.Cu split map and identify any B.Cu signal that crosses a power split. For each crossing, either reroute or place a return-path bridge cap (typ 100 nF GND-to-power) at the crossing.

### B-3. Current-sense lines (SOA1/SOB1/SOC1/SOC2) split between F.Cu and In2.Cu
- /SOC1: 11 F.Cu + 11 In2.Cu segments.
- /SOA1: 8 F.Cu + 6 In2.Cu segments.
- /SOB1: 8 F.Cu + 5 In2.Cu segments.
- /SOC2: 16 F.Cu + 7 In2.Cu segments.
At 8 A peak motor current with ~10 mOhm shunt these are ~80 mV signals into an MCU ADC. Layer-jumping them through the noisy In2.Cu split-plane region risks coupled noise from adjacent +BATT/VCC pours and switching transients. Strongly recommend keeping each sense line on a single layer with In1.Cu (solid GND) as its reference. If In2.Cu use is unavoidable, ensure the trace runs entirely over the In2.Cu **GND** fill region, not over the +BATT/VCC pours.

## CRITICAL

### C-1. Verify In2.Cu split lines do not run under USB D+/D-
- USB D+/D- are routed entirely on F.Cu (21+20 segments, 0.2 mm width). Their primary reference is In1.Cu (210 um below) — that is solid GND, so USB SI is good in principle.
- However, copper on layer 4 (B.Cu) directly under USB will couple weakly. Confirm there are no narrow GND-pour necks or B.Cu split lines directly under the USB pair that could create a secondary return-path issue. (Lower priority since In1.Cu is the dominant reference.)

### C-2. Plane voiding / Swiss-cheesing risk on In1.Cu
607 through-vias on a 76.95 x 36.93 mm = 2831 mm² board = ~0.21 vias/mm². On In1.Cu each via is an antipad. Visual inspection of In1.Cu PNG shows the GND plane remains continuous everywhere — no obvious slot or break — but the area under the DRV8316 thermal pads has heavy via concentration. Verify with a magnified view that none of these via clusters has formed a continuous slot wider than ~1.5 mm in the GND plane (would force return current to detour). Visually it looks acceptable.

### C-3. +3.3V on In2.Cu is a small, narrow pour (`3.3V_BCC`, priority 2, single layer)
The +3.3V pour on In2.Cu is the lowest-priority of the power pours, meaning it gets carved away wherever VCC, +BATT or VBUS overlap. With 16 +3.3V segments also routed on In2.Cu and 110 +3.3V segments on F.Cu, the +3.3V net depends mostly on F.Cu pour for distribution. **Verify +3.3V pour reaches all critical 3.3V loads (MCU VDD, encoder VDD, MagAlpha VDD, CAN transceiver V_IO).** A small In2.Cu +3.3V island provides limited bypass capacitance benefit — most decoupling effort needs to be local-cap-driven.

### C-4. Power plane segmentation count
In2.Cu carries at least 4 different power nets as pours (+BATT/24V, VCC, +5V, +3.3V) plus VBUS as segments. Any split between pours is an EMI antenna unless bridged by GND vias on both sides. The 367 GND vias plus heavy GND fill in the gaps should bridge most of these reasonably, but per IPC/Henry Ott practice each split should ideally have a GND moat on at least one adjacent layer — In1.Cu solid GND directly above provides that. **OK in principle, but worth visually confirming during gerber review that the GND fill on In2.Cu fills all the gaps between power pours rather than leaving signal-routing channels with no GND beside them.**

## NITS

### N-1. CAN_H vs CAN_L segment count mismatch
CAN_H = 62 segments, CAN_L = 42 segments. Diff pairs should be roughly mirror-symmetric. Cause is probably the via-jumping pattern or a length-tuning meander. Length-match the pair within 1 mm at the receiver.

### N-2. /BUCK net (5 V buck switch node) routed on In2.Cu
10 segments of `/BUCK` (the buck switch node) on In2.Cu, plus a F.Cu pour. Switch nodes are noisy (high dV/dt). Inner-layer routing puts the noise between two GND/power references which is actually quieter than running it on top — but verify the In2.Cu BUCK trace is short and goes directly from buck IC switch pin to inductor without long detours.

### N-3. Inner-layer copper thinness (15 um)
The KiCad default 15 um inner copper (~0.5 oz) is half the F.Cu/B.Cu thickness (35 um). For the 0.8 mm wide power segments on In2.Cu (+5V, +BATT, BUCK), 15 um at 0.8 mm carries roughly 1.5-2 A continuous (IPC-2152 internal). Verify these segments are not the sole power path to high-current loads — they should be backed by F.Cu/B.Cu pours and vias.

### N-4. Motor phase currents are NOT on inner layers (good)
PHA1/PHA2/PHB1/PHB2/PHC1/PHC2 (motor phases, up to 8 A peak) are F.Cu pours only — zero inner-layer routing. Smart choice given the 15 um inner copper limitation.

## Notes (positives)

- **In1.Cu is a textbook solid GND plane.** No splits, no signals, just antipads. Ideal reference for F.Cu signals.
- **High GND via stitching density.** 367 of 607 through-vias are on GND (~60%). Heavy GND-via population around DRV8316 thermal pads, BK22 power connectors, and (presumably) USB shield as expected.
- **Stackup file annotated with real materials** (Nan Ya NP-155F, er 4.4/4.43, loss tan 0.02). JLCPCB-compatible. Good.
- **Motor phases kept off inner copper.** Avoids the 15 um current-density limit.
- **No DRC plane-integrity errors.** 12 starved_thermal warnings exist (worth checking at fabrication for individual pad-to-plane connections) but no track_dangling on inner layers, no plane-related copper_edge_clearance issues.
- **CAN_H/L have 5 stitching vias each on the GND net** — implies someone placed return-path vias near the diff pair via transitions. Verify positions next to the CAN_H/CAN_L vias.

## Recommended actions before fab

1. **(Blocker)** Open the board and visually trace each B.Cu signal to verify it does not cross any In2.Cu plane split (where +BATT meets VCC, VCC meets +5V, etc.) without a GND bridge cap or GND stitching at the crossing. Particular attention to /SOA*, /SOB*, /SOC*, ADC5_IN1, ADC5_IN2, CAN_H, CAN_L.
2. **(Blocker)** Verify CAN_H/L diff pair: paired vias for each layer transition (CAN_H via and CAN_L via within ~1 mm of each other), GND stitch via within 2-3 mm of every diff via, total pair length match within 1 mm.
3. **(Critical)** Run the BOM-of-bridge-caps check: each plane split on In2.Cu should have at least one ceramic cap (tens-to-hundreds of nF) bridging the two power pours where signal traces cross.
4. **(Critical)** Move /SOA1, /SOB1, /SOC1, /SOC2 onto a single layer (preferably F.Cu so In1.Cu solid GND is the reference) and avoid routing them across In2.Cu split-plane regions.
5. **(Nit)** Ask fab to bump inner copper to 1 oz (35 um) if the cost is reasonable — would relax current limits on In2.Cu power segments and reduce IR drop.
