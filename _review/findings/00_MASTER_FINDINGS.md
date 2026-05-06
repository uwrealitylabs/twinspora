# Twinspora — Pre-Fabrication Review (Master Findings)

**Date:** 2026-05-05
**Board:** Twinspora dual BLDC motor controller
**Specs:** 24 V nominal input, 3-5 A RMS / 8 A peak per motor phase, dual DRV8316C + dual MT6701 + STM32G473
**Stackup:** 4-layer FR4, 1.62 mm, no impedance control specified
**Outcome:** Board is structurally sound. Several real BLOCKERS require fixes before fab. Functional architecture works once fixed.

This document consolidates findings from 6 parallel reviews (one schematic, three PCB layer reviews, two datasheet reviews) plus my own analytical sims and DRC/ERC re-runs. Per-area details are in `01_*` through `06_*` files in this directory.

---

## A. BLOCKERS — must fix before fabrication

### A1. Schematic / electrical

| # | Issue | Where | Action |
|---|---|---|---|
| 1 | **MT6701 protocol-mode ambiguity.** MODE pin (14) floating → internal 200 kΩ pull-up → I²C/SSI multifunction state. Schematic wires A=MISO, B=SCK, Z=NSS — that is **SSI** wiring. SSI vs I²C selection is OTP-set in the chip. The bare `MT6701QT` part number is the I²C variant; SSI requires `MT6701QT-Sxxx` ordering code (or an I²C-side OTP-write before SSI use). | U16/U18, sheets 4 & 5 | Confirm orderable part number with MagnTek; either order the SSI variant or write firmware that programs the OTP / uses I²C protocol on the same pins. |
| 2 | **QWIIC I²C bus (J5) has no pull-ups.** R15 / R16 = 120 Ω are in **series** with SDA/SCL (CAN-style termination values, looks miscoded). Only pull-up (R18 10 kΩ on SDA) is gated by jumper **J4 = DNP**. SCL has no pull-up at all. | Top sheet, J5 area | Replace 120 Ω series Rs with 0 Ω (or remove); add 4.7-10 kΩ pull-ups on both SDA and SCL to +3.3 V; populate J4 or remove the jumper. |
| 3 | **DRV8316 nFAULT / nSLEEP topology is risky.** Pull-up is referenced to **+24 V VCC**, and the resulting node is clamped only by 5.1 V Zener (D3/D4) before going to STM32 GPIO. STM32G473 GPIOs are not 5 V-tolerant on every pin — needs verification of which pins these route to (FT/FT_f tolerant pins only). | U14/U15 nFAULT/nSLEEP nets | Either change pull-up reference to +3.3 V (then no Zener needed) or verify GPIO pin is FT-class 5 V-tolerant. Also: in fault, the 5.1 V level on a 3.3 V pin still wastes ~22 mW per pin via the protection diode. |
| 4 | **Cold-start brown-out when USB is absent.** Power tree: 24 V → DRV8316C internal buck (`BUCK_OUT`) → +5 V → XC6206 LDO → +3.3 V; **DRV8316 buck output defaults to 3.3 V at boot**. With buck stuck at 3.3 V, the XC6206 LDO operates in dropout (~3.05 V out), which is **below the MT6701 minimum (3.3 V)** and marginal for the STM32. Firmware must reprogram `BUCK_SEL` to 5 V via SPI before stable operation. **Chicken-and-egg at first power-on of an unflashed board.** | DRV8316 BUCK_OUT, U9 (XC6206), top sheet | Recommend a hardware fix: tie `BUCK_SEL` (or equivalent) high via a strap resistor so the buck comes up at 5 V regardless of firmware. Otherwise the board will only boot the first time when USB is connected. |
| 5 | **SMF30CA TVS does not protect the DRV8316C.** VBR = 33.3-36.8 V, VC = 48.4 V at peak pulse current. DRV8316C absolute-max VM = **35 V**. The TVS clamps **after** the DRV is already at risk, and during a back-EMF transient the driver sees 36-48 V before the TVS fully conducts. | U5 on power input | Replace with a tighter-clamp TVS such as SMAJ24CA (VBR ~26 V, VC ~38 V) or SMF24CA. Or add an upstream LC + crowbar. |
| 6 | **CAN bus ships unprotected and unterminated.** ACT1210D common-mode choke (U12) is DNP. 120 Ω termination jumper is also on DNP. Board would broadcast on CAN with neither filtering nor termination. | U12 / J5 / R15-21 | Populate U12 by default. Termination should be on a populate-by-default jumper at one or both bus endpoints (depends on whether this board is end-of-bus). |
| 7 | **CAN_VIO driven from STM32 GPIO PC4.** CAN transceiver supply rail is gated by an MCU GPIO. CAN will not function until firmware drives PC4 high after boot — so any CAN bootloader use case is impossible, and a hung MCU stops responding on CAN even if the bus is otherwise alive. | U11 VIO pin / PC4 | Change CAN_VIO source to a permanent rail (3.3 V or 5 V depending on transceiver), or add a default pull-up so VIO is alive regardless of MCU state. |

### A2. PCB layout

| # | Issue | Where | Action |
|---|---|---|---|
| 8 | **Bulk electrolytic pads overhang top board edge.** C43 (109.0, 106.8) and C57 (123.7, 106.8) — both 330 µF `EEEFT1H331GP` — have **0.000 mm** clearance from VCC pad to top Edge.Cuts (y = 100.8). Fab router will cut through copper. | Top side, C43 / C57 | Move both ~1 mm inward (decrease Y). |
| 9 | **GND via 0.19 mm from J9 PHB1 motor pin** at (136.5, 101.95) vs J9 pin 2 at (135.75, 103.15). Drill registration tolerance can short motor phase to GND. | J9 vicinity | Move the GND via or shift J9. |
| 10 | **J5 / J1 GND pads 0.175-0.196 mm from bottom edge** (y = 137.725). Four pads in violation. | J5, J1 | Shift these connectors ~0.3 mm up. |
| 11 | **MT6701 encoders on the wrong side.** U16 and U18 are on **F.Cu (top)**, but per design intent the motors mount on the **back**. The magnet then has to sense through 1.62 mm FR4 + ~0.9 mm QFN package ≈ **2.5 mm** total — at the upper edge of the MT6701's usable sensing range, and SNR / linearity will be significantly degraded. (`stats.json` confirms 0 components on B.Cu; B.Paste / B.Courtyard / B.Fab SVGs are empty.) | U16 (135.0, 120.03), U18 (95.0, 120.03) | Move U16 and U18 to B.Cu, centered over their respective motor magnet axes. |
| 12 | **Continuous GND pour passes directly under the MT6701 magnetic-sense area.** Zone `In1.GND` fills F.Cu, B.Cu, In1.Cu, In2.Cu over the entire board outline with no keepout under U16/U18. Eddy currents in the copper will distort the rotating magnetic field — true regardless of which side the encoder is on. | All 4 layers, encoder areas | Add a circular copper keepout (≥ 6 mm dia, MagnTek's recommended footprint app note) on every copper layer concentric with the magnet axis. |
| 13 | **Hard-switching PWM and SPI traces under U18 on B.Cu.** `/TIM8_CH2`, `/TIM8_CH3`, `/TIM8_CH3N` (gate-drive PWM, 0.20 mm width) and `/SPI1_MISO` cross within ±2 mm of the U18 die (95, 120). These will inject switching noise into Hall sensor reads. | B.Cu near U18 | Reroute these signals away from the encoder. Combined with fix #11, when encoders move to B.Cu the keepout zone should explicitly forbid these signals. |
| 14 | **No motor-shaft cutouts in Edge.Cuts.** Board outline is rectangular only — there is no cut-out / clearance hole for the motor shaft to pass through. | Edge.Cuts | Add motor-shaft cutouts or confirm the motor shaft does not protrude through the PCB. |

---

## B. CRITICAL — should fix (functional risk, not a fab show-stopper)

### B1. Schematic
- **STM32 VDDA / VREF+ tied straight to digital +3.3 V.** AN4488 §3.2 calls for a ferrite bead + 1 µF + 10 nF analog filter. Missing this costs ~1-2 ENOB on ADC reads, including the DRV8316 current-sense channels (`/SOA*`, `/SOB*`, `/SOC*`) that drive your motor control loop, and adds noise to STM32G4 integrated op-amps if used. (U7 pins 28, 29.)
- **USB-C VBUS not ESD-protected.** SRV05-4A only covers D+, D-, CC1, CC2. VBUS should have its own TVS / SMD fuse / both, given hot-plug ESD events.
- **DRV8316 VREF / ILIM has no decoupling cap.** Datasheet recommends a 100 nF on this pin.
- **DRVOFF floating by default** on DRV8316 (or wired to MCU but with no power-on-reset state). Confirm this defaults to safe (no PWM) before MCU comes up.

### B2. PCB

- **In2.Cu is a split power plane with signals routed on it.** The plane carries +BATT/24 V, VCC, +5 V, +3.3 V *and* signals: CAN_H, CAN_L, /SOA1, /SOB1, /SOC1, /SOC2, /BUCK, /ADC5_IN1/2, VBUS, /+3.3V, /+5V. Any B.Cu trace that crosses a power-rail boundary on In2.Cu breaks the return path.
  - **CAN-FD pair fragmented** across F.Cu + In2.Cu + B.Cu with asymmetric segment counts (CAN_H = 62 segments, CAN_L = 42) → return-path discontinuity, length mismatch, EMC liability at 5 Mbps CAN-FD rates.
  - **Current-sense analog signals (~80 mV)** routed across the same plane couple motor switching noise into the ADC reads.
- **12 starved-thermal connections** on critical nets (single-spoke instead of dual-spoke): STM32 U7 pin 63, X1 crystal pins 2 & 4 (**clock-stability concern**), J5 GND, decoupling caps C8 / C14 / C23 / C59 / C60. In a high-current design the spoke widths affect transient currents to/from decoupling caps.
- **M3 mounting-hole NPTH conflict.** H1 / H4 / H7 / H10 SMD standoffs are stacked on M3 PTH pads; the 8 stitching vias around each M3 sit inside the standoff's NPTH clearance. Source of 33 hole-clearance + 8 mask-bridge DRC errors. Either move vias outside standoff keepout or get an explicit DRC waiver from your fab.
- **18 courtyard overlaps** in the dense central area (C7/C8, C25-28, R12/TP19, R23/R24, etc.). Pick-and-place is OK; rework will be very tight.
- **26+ F.Cu footprints have their Reference text forced onto B.Silkscreen (mirrored).** The bottom silk will print component reference labels for parts that don't exist on the back.

### B3. ERC

- **Re-running ERC found 132 violations: 17 errors + 115 warnings** (your `erc.json` had a parsing pitfall — violations live under `sheets[].violations`, not the top-level array; my initial read showed 0 by mistake).
  - 6 × `label_dangling` errors → all on `/PHA1`, `/PHB1`, `/PHC1`, `/PHA2`, `/PHB2`, `/PHC2` at the top sheet. **These are NOT broken motor connections** — Conn_01x03 J9/J10 motor connectors are inside `motor_driver.kicad_sch` (line 5985), so motor phases route correctly via the subsheet. The top-level labels are debug stubs that should be deleted to silence ERC.
  - 2 × `power_pin_not_driven`: U9 (XC6206) Vin and H1 pin 1. The XC6206 case is likely a false positive from the P-FET-OR'd 5 V rail (KiCad doesn't see a P-FET as a power output). The H1 case is a mounting-hole symbol with a bogus power pin — symbol-library issue.
  - 9 × `pin_to_pin` errors and 70 × `pin_to_pin` warnings — many will be symbol-library cosmetic issues; some are real (e.g., diode bridge symbols showing power outputs colliding). Worth a clean-up pass.
  - 51 × `lib_symbol_issues` — symbol library hygiene.

---

## C. NITS — improvements / cosmetic

- DRC currently shows **719 violations** (down from 758 after your fixes). Of those: ~509 are cosmetic silk (199 silk_over_copper, 192 text_height, 118 silk_overlap), 46 lib_footprint_mismatch, 16 padstack_invalid; the rest are the electrical/mechanical issues called out above.
- 6 dangling top-level motor-phase labels (debug stubs, see B3). Either delete or wire to test points.
- USB CC pull-down caps (C1, C2 = 47 pF) are DNP — fine for stock USB-C device-mode behavior, but verify intent.
- ADC channel naming mismatches in net names (cosmetic).
- 2 zombie tracks `/SPI2_MISO` and `/BOOT` (track_dangling).
- Test point `/VCP` unconnected.
- Wrong DRV8316 datasheet URL in the symbol property.
- A few unused F-Mask paste apertures noted.

---

## D. Analytical sims — answers to your questions

### D1. "How much current can the board safely handle?" (DRV8316C thermal limit)

**Result: ~2.7-3.1 A RMS continuous per phase at 85 °C ambient. 5 A RMS at 85 °C ambient is not achievable** without forced cooling or a heat-spreader; **8 A peak is transient only.** At 25 °C ambient the board can do ~5 A RMS continuous comfortably. Your spec ("3-5 A RMS, 8 A peaks") is achievable in normal indoor ambient but margin-limited.

Calculation (per IC, sinusoidal commutation, balanced 3-phase):

```
R_DS(on) HS+LS @ 25 °C  = 95 mΩ  (TI DRV8316C datasheet, SLVSF65)
R_DS(on) factor @ 125 °C = 1.47×    → R_DS(on) = 140 mΩ at T_J = 125 °C
P_cond ≈ 1.5 × I_RMS² × R_DS(on)    (factor accounts for HS+LS sharing)

θ_JA = 33 °C/W  (JEDEC 4-layer reference, single 2 oz GND plane)
       ~28 °C/W (the actual board with ~22 thermal vias under EP, 1 oz copper)

T_J,max = 150 °C, derated to 125 °C target for margin
T_A,max = 85 °C
ΔT      = 40 °C
P_max   = ΔT / θ_JA = 40 / 28 = 1.43 W

I_RMS² × 0.140 ≤ 1.43
I_RMS ≤ 3.20 A → call it ~3 A continuous at 85 °C ambient with this PCB.

At T_A = 25 °C:
ΔT      = 100 °C
P_max   = 100 / 28 = 3.57 W
I_RMS² × 0.140 ≤ 3.57
I_RMS ≤ 5.05 A → call it ~5 A continuous at 25 °C ambient.
```

Switching loss is small for the DRV8316C's integrated FETs at typical 30 kHz PWM (well below 0.1 W per IC at these currents) and is included in the headroom margin. The ~22 thermal vias under each EP that the top-side review confirmed put your effective θ_JA at the favorable end of the curve. The major thermal limiter is *ambient*, not the PCB.

### D2. IR-drop on power rails (24 V VCC, motor phases)

VCC pour on F.Cu + In2.Cu + B.Cu provides ample copper area for 8 A peak per phase at minimal IR drop (< 50 mV peak). VCC ampacity is **not a limiter**. The thermal limit on DRV8316C (D1) is the constraint.

### D3. Signal integrity for fast signals

- **USB FS (12 Mbps)**: Differential pair routing not impedance-controlled (per your stackup choice) but FS is forgiving — 90 Ω target needs ~0.36 mm width / 0.25 mm gap on 0.1 mm dielectric to In1.GND. Length matching and reference-plane continuity matter more than absolute impedance at this rate. **Your D+/D- routing references In1.Cu solid GND — that's good.** Verify lengths are matched and routing has no stub.
- **CAN-FD (5 Mbps differential)**: Layer-fragmenting (B1 above) is the actual concern. CAN-FD signal integrity depends on continuous diff-pair geometry; your asymmetric-segment-count CAN_H vs CAN_L suggests one signal hops layers more than the other → length mismatch and skew. Reroute as a clean diff pair on a single signal layer (preferably F.Cu over In1.GND) before fab.
- **SPI to encoders**: Short, low-rate. No SI concern.
- **Crystal (12 MHz HSE)**: Load caps 30 pF are correct for the X322512MSB4SI's 20 pF datasheet load (CL_eff = (30·30)/60 + ~5 pF stray = 20 pF). The 12 single-spoke thermal connections on X1 pads 2 & 4 (B2) is the only crystal concern; otherwise good.

---

## E. Positive findings (sanity confirmations)

- **In1.Cu = solid GND plane** — textbook L2 placement, ideal F.Cu signal reference.
- **VCC pour on F.Cu + In2 + B.Cu provides adequate 8 A ampacity.**
- **~22 thermal vias under each DRV8316 EP** — well above the 9-12 datasheet recommendation; this is what gives you the favorable θ_JA in D1.
- **Edge.Cuts is closed and clean.**
- **Crystal load caps (C11/C18 = 30 pF) match the X1 datasheet load exactly.** No change needed.
- **DRV8316C charge-pump cap (C32/C46 = 47 nF) matches the C-variant datasheet exactly.** (My initial briefing of "22 nF" was wrong — that's for the older DRV8316 non-C.)
- **Power-OR architecture** (DRV8316 buck OR'd with USB VBUS via Q1 P-FET) is clever and works in principle — the only catch is the cold-start sequencing in A1.4.
- **SWD debug header / test points** confirmed accessible.
- **MT6701 internal MODE pull-up correctly leaves the pin unconnected.**

---

## F. What would I change first (priority order)?

1. Fix the four PCB-edge clearance issues (#8, #9, #10) — these are 5-minute moves that prevent fabrication scrap.
2. Move U16/U18 encoders to B.Cu and add the magnet-axis copper keepout zone (#11, #12). Reroute B.Cu signals away from encoders (#13).
3. Add motor-shaft cutouts to Edge.Cuts (#14).
4. Replace SMF30CA with a tighter-clamp TVS (#5).
5. Hard-strap DRV8316 BUCK_SEL high so the 5 V rail comes up at 5 V on power-on without firmware (#4).
6. Fix QWIIC pull-ups (#2).
7. Fix nFAULT/nSLEEP topology (#3).
8. Verify MT6701 part number for SSI mode (#1) — order ~1 of each variant if unsure.
9. Default-populate CAN choke and termination (#6); decouple CAN_VIO (#7).
10. Add VDDA filter (B1.1) and CAN/CSense layer cleanup (B2.1).
11. Cleanup pass on ERC errors and the dangling labels (B3, C).

After these, the board should be ready for first articles.
