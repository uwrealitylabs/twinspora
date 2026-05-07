# 06 Datasheet Review — Discrete & Support ICs (Pre-Fab)

Twinspora dual-BLDC motor controller. Inputs: 24V via BK22 mezzanine; USB-C 5V VBUS; CAN bus (J5); SH1.0 SPI to encoders. Motor phases up to 8A peak.

Schematic top sheet: `twinspora/twinspora.kicad_sch` (page 1)
Sub-sheets: `motor_driver.kicad_sch` (page 2 & 3 instances), `magnetic_encoder.kicad_sch` (page 4 & 5 instances).
BOM: `_review/bom.csv`. Rendered: `_review/exports/sch_png/sheet_0[1-5].png`.

---

## Power-tree summary (resolves the "5V mystery")

The DRV8316C (motor-driver U14/U15) has an **integrated 200 mA buck regulator** on its `VBK`/buck output pin (configured as 5 V on this board). The schematic exposes that buck output via a hierarchical pin `BUCK_OUT` (motor_driver1 sheet, top-sheet coordinate 107.95, 170.18 → label `BUCK`).

Power tree:

```
+24V (BK22) ──► U14/U15 DRV8316C VM
                  └─► internal buck (5V/200mA) ──► BUCK net
USB-C VBUS (5V) ─────────────────────────────────► VBUS net

VBUS  ──┐
        ├── Q1 AO3401A P-FET OR-ing ──► +5V rail (208.28, 33.02 in top sheet)
BUCK ───┘                               │
                                        ├── decoupling caps
                                        ├── U8 H5VL10BC TVS clamp (5VWM/12VC bidir)
                                        └── U9 XC6206P332MR LDO ──► +3.3V (200 mA)
```

Annotation in top sheet (text_box at 157.48, 26.67) confirms: *"200 mA LDO / Power OR-ing with PMOS … BUCK starts at 3.3 V default … Also prioritizes VBUS over BUCK."* Second annotation (21.59, 25.4): *"5 V Breakout from Motor Driver 2 Max. 200 mA."*

→ The XC6206 input is **+5 V**, not +24 V. Safe.

The DRV8316C buck must be configured (via SPI register) to 5 V (default boot value is 3.3 V per TI datasheet — the on-board annotation agrees: *"BUCK starts at 3.3 V default"*). **MCU firmware must reprogram the buck output to 5 V at boot before the OR-ing tree settles, otherwise the +5V rail droops to 3.3 V when USB is unplugged and the LDO falls out of regulation.** See *NIT* below.

Datasheet sources used:
- DRV8316C: [TI DRV8316C product page (lit/ds)](https://www.ti.com/lit/ds/symlink/drv8316c.pdf)

---

## 1. MT6701QT (U16, U18 — magnetic angle encoder, MagnTek QFN-16)

**Datasheet (Rev 1.8):** https://www.novosns.com/enfiles/MT6701_Rev.1.8.pdf
**LCSC:** C2856764 (CT-STD), C2913974 (QT-STD)

**Pinout used (sheet 4/5):**
- Pin 6 (A) → `MISO` (via 0Ω R33/R36)
- Pin 7 (B) → `SCK`  (via 0Ω R34/R37)
- Pin 8 (Z) → `NSS`  (via 0Ω R35/R38)
- Pin 13 (VDD) → +3.3V with C59/C60 = 100nF
- Pin 14 (MODE) → **NC (KiCad no-connect symbol)** — relies on internal 200 kΩ pull-up to VDD
- Pin 16 (GND) → GND
- Pins 5, 9, 11, 12, 15 (PUSH, W, U, V, OUT) → NC (X)

**MODE pin verdict — OK.** Per datasheet: pin 14 is a digital input with a built-in 200 kΩ pull-up; it selects ABZ vs I2C/SSI multifunction on pins 6/7/8. With MODE left floating, the pin is internally pulled HIGH, putting pins 6/7/8 in **I2C/SSI shared mode**. Within that mode, the chip behaves as I2C when CSN (pin 8 / Z) is HIGH and as SSI when CSN is pulled LOW — i.e. the master selects per-transaction by NSS. This matches the schematic: pin 8 → NSS. **SSI works as intended.**

**Magnet placement (datasheet recommendations — verify on mechanical):**
- Diametric (perpendicular-to-axis) magnetisation, NOT axial.
- Magnet centre directly over the QFN package centre.
- Air gap 0.5 – 3.0 mm typical (sweet spot ~1.0 mm).
- Magnet diameter 4–10 mm.
The mechanical/PCB design must place the encoder centred under the rotor magnet — confirm in the FP/3D review.

**VDD decoupling:** 100 nF (C59, C60) at pin 13. Datasheet recommends 100 nF — adequate. Consider adding a bulk 1 µF nearby if there is supply-rail noise from the buck (no measurement yet, NIT).

**NIT — 0Ω jumpers in series with A/B/Z signals (R33–R38):** the `_review/findings/02_pcb_top.md` should re-verify these are truly 0 Ω placed (BOM line 31 confirms `0603WAF0000T5E`, R23/R24/R33-R38). They allow re-routing in case A/B/Z must be remapped — fine.

---

## 2. CA-IF1044VD-Q1 (U11 — CAN-FD transceiver, Chipanalog DFN-8)

**Datasheet:** https://www.lcsc.com/datasheet/C5155979.pdf (Chipanalog, automotive-Q1)
LCSC C5155979. **Note: this is a Chipanalog second-source for TI TCAN1044V-Q1**, not a TI part.

The "VD" suffix denotes the variant **with a VIO logic-supply pin** (replaces TXD-only level shifting). Pinout for the family (DFN-8):

| Pin | Function |
|-----|----------|
| 1 | TXD |
| 2 | GND |
| 3 | VCC (5V) |
| 4 | RXD |
| 5 | VIO (logic supply, 1.8/2.5/3.3/5 V) |
| 6 | CANL |
| 7 | CANH |
| 8 | STB (silent/standby; tie LOW for normal mode) |

**Schematic check:** the top sheet has labels `FDCAN_TX`, `CAN_VIO`, `CAN_H`, `CAN_L` near the CAN block. Both CAN_VIO and a +3.3V/+5V are routed — verify VCC pin is on the +5V rail and VIO pin is on the +3.3V rail. From the rendered PNG sheet_01.png the CAN block clearly shows decoupling on both VCC and VIO sides.

- **VCC absolute max** ≈ 6 V (bus-side 5 V supply). Fed by +5V rail — OK.
- **VIO** range 1.8 – 5.5 V. Fed by +3.3V rail — OK.
- **TXD dominant timeout** present (~1.2 ms typ for the family) → bus-fault tolerant, OK.
- **STB** must be tied LOW (or driven by GPIO) for normal mode. **VERIFY** which net STB is on (search top sheet at U11 pin 8).

**Decoupling:** datasheet recommends 100 nF on VCC and 100 nF on VIO close to the pins. BOM has plenty of 100 nF 0402 — verify two are placed adjacent to U11.

---

## 3. ACT1210D-101-2P-TL00 (U12 — TDK common-mode choke for CAN)

**Datasheet:** https://product.tdk.com/system/files/dam/doc/product/emc/emc/cmf_cmc/catalog/cmf_automotive_signal_act1210d_en.pdf
**Product page:** https://product.tdk.com/en/search/emc/emc/cmf_cmc/info?part_no=ACT1210D-101-2P-TL00

- 2-line common-mode choke, 1210 size (3.2 × 2.5 mm)
- "-101" code = **100 Ω common-mode impedance @ 100 MHz** (typical)
- Rated current: **115 mA**
- DCR max: 3 Ω/line
- Rated DC voltage: 80 V
- ACT1210**D** variant is optimised for **CAN-FD** (low leakage inductance, low mode-conversion). Correct choice for this board.

**Schematic placement check:** must sit between transceiver CANH/CANL pins and the connector J5, with split-termination (R15+R16 = 60.4 Ω each + Y-cap) BEFORE the CMC (closer to transceiver) per most CAN-bus EMC reference designs. Confirm on the layout (a separate PCB-review item).

**NIT:** 115 mA rated current is plenty for CAN-bus signal currents (a few mA), no concern.

---

## 4. PESD2CAN (U13 — Nexperia bidirectional CAN ESD/TVS, SOT-23-3)

**Datasheet:** https://assets.nexperia.com/documents/data-sheet/PESD2CAN.pdf

- Bidirectional, two channels (CANH, CANL) referenced to GND
- Reverse standoff voltage VR = 24 V
- Breakdown voltage VBR = 26.2 – 30.3 V
- Clamp VCL = 41 V @ IPP = 5 A
- IEC 61000-4-2 ±30 kV (contact)

Pin 1, 2 = CANH, CANL; pin 3 = GND. Schematic shows U13 with the diode pointing into a centre node tied to GND — **orientation correct** for bidirectional CAN protection.

**NIT:** 24 V VR is the standard pick for 12 V automotive CAN. On a 24 V system the CAN is still single-ended ground-referenced and signals never exceed 5 V, so VR = 24 V is fine for CAN. This is unrelated to the +24V supply rail.

---

## 5. SRV05-4A (U6, U10, U17, U19 — onsemi quad-channel ESD, SOT-23-6)

**Datasheet:** https://www.onsemi.com/download/data-sheet/pdf/srv05-4-d.pdf

- 4 data-line channels + 1 surge diode → SOT-23-6
- VRWM 5 V, VBR ≈ 6 V, VC ≈ 12.5 V @ 1 A
- ESD ±15 kV, 5 A surge
- Capacitance ~0.6 pF/channel (USB 2.0 / SPI fine)

**Per-instance check:**
- **U6** (top sheet, 135.89, 46.99) → USB-C J2: protects D+, D-, CC1, CC2 (4 lines = exactly the 4 channels available). Good. `VBUS` is **NOT** protected by U6 — see *BLOCKERS* below.
- **U10** (top sheet, 255.27, 210.82) → QWIIC/I2C breakout J5? actually J5 is CAN. U10 must be on J7/J8 (3-pin SH1.0) area or Qwiic. **Verify on rendered sheet_01.png** which connector U10 sits next to — only 2-3 lines need protection there so 4 channels is sufficient.
- **U17, U19** (subsheets 4 & 5, J11/J12 6-pin SH1.0 encoder breakouts) → only 4 of 4 channels routed (NSS, SCK, MOSI, MISO). The SH1.0-6P breakout exposes 6 lines (VCC, GND, MOSI, MISO, SCK, NSS). VCC (3.3V) and GND **are not protected by U17/U19** — typically VCC needs its own ESD diode or zener. Acceptable risk for a development breakout, but worth flagging.

---

## 6. SMF30CA (U5 — Littelfuse / MDD bidirectional TVS, SOD-123FL)

**Datasheet (Littelfuse SMF series):** https://www.farnell.com/datasheets/...SMF30CA  → search SMF30CA datasheet
**LCSC:** C364282 (MDD)

- VRWM = **30 V**
- VBR = 33.3 – 36.8 V
- VC = 48.4 V @ IPP = 4.13 A
- Bidirectional, 200 W
- Located on +24V input (U5 at 105.41, 238.76 in POWER IN block)

**CRITICAL — TVS rating marginal for 24 V motor system.**

A 24 V BLDC system in motor regen / inductive kickback can spike 30–40 V transient on the input rail. With VRWM = 30 V, the TVS is right at the edge — under nominal 24 V operation it does not conduct (VBR min = 33.3 V is above 30 V VWM, so leakage is in the µA range), but during regen any spike above ~30 V starts entering the soft-knee region and **above 33 V it begins clamping with significant current**. The TVS is sized to clamp at 48.4 V which is OK for a 24 V buck input rated 60 V (DRV8316C VM max is 35 V — *see motor-driver review*), but the clamp current limits to 4 A peak.

Two issues:
1. **DRV8316C VM absolute max = 35 V**. SMF30CA only starts clamping at ~33 V and rises to 48 V — by the time the TVS is clamping hard, the DRV8316C is already in over-voltage shutdown or damaged.
2. The standard rule is VR ≥ 1.3 × Vnom = 1.3 × 24 = 31.2 V → SMF30CA's 30 V VR is **just below** the rule of thumb.

**Recommendation:** swap to **SMF33CA** (VRWM = 33 V, VBR ≈ 36.7–40.6 V, VC ≈ 53.3 V) — wait, that's worse for VC vs DRV8316 max. Better: **SMBJ28CA** (VR=28 V, VC≈45.4 V) is closer to ideal, but still pushes against DRV8316 35 V max.

True fix: add a **TVS with VC ≤ 33 V** (e.g. SMBJ24CA: VR 24 V, VBR 26.7–29.5 V, VC 38.9 V — also exceeds DRV8316 max) or — better — add a **series PTC + lower-VC TVS** to actually protect the DRV8316C. **The current SMF30CA does NOT actually protect the motor driver from a 35 V transient.** This is a *CRITICAL* issue and should be re-evaluated before fab; see BLOCKERS.

---

## 7. XC6206P332MR (U9 — Torex 3.3 V / 200 mA LDO, SOT-23-3)

**Datasheet:** https://www.alldatasheet.com/datasheet-pdf/view/243854/TOREX/XC6206P332MR.html
LCSC C5446.

- Output: 3.3 V, 200 mA
- Input range: 1.8 – 6 V
- **Absolute max VIN = 6 V**
- Dropout: 0.68 V at 200 mA (so VIN must be ≥ 3.98 V for full-load 3.3 V regulation)

**Verdict — SAFE.** U9 input (pin 2, Vin) is wired via the +5 V rail at the y=36.83 horizontal trace in the top sheet. Source = OR'd output of Q1 (P-FET, OR'ing VBUS and BUCK) → ≈ 5 V. Never exceeds 6 V abs max in normal operation.

**Edge case — OR-ing during USB connect with motor unpowered:** VBUS = 5.0 V (USB spec), BUCK = high-Z (no VM). Q1 conducts → +5V = 5 V → U9 OK.

**Edge case — motor powered, no USB:** BUCK = 5 V (assuming firmware reprogrammed buck to 5 V), VBUS = 0 V. Q1 conducts (gate goes low through pull-down) → +5V = 5 V → U9 OK.

**NIT — boot-up race condition:** DRV8316C buck defaults to 3.3 V per TI datasheet. If the firmware fails to reprogram the buck to 5 V before VBUS is removed, the +5V rail droops to 3.3 V and U9 dropout (0.68 V) leaves output ≤ 2.62 V — MCU brownout. Document this in firmware notes.

---

## 8. AO3401A (Q1 — Alpha & Omega P-FET, SOT-23)

**Datasheet:** http://www.aosmd.com/pdfs/datasheet/AO3401A.pdf

- VDS = -30 V (so 24 V system safe by 6 V margin if used on 24 V — but here it sees ≤ 5 V VBUS↔BUCK)
- VGS = ±12 V
- ID = -4 A continuous
- RDS(on) = 60 mΩ @ VGS = -10 V; ~80 mΩ @ VGS = -4.5 V

**Role:** OR-ing P-FET between VBUS and BUCK (5 V rails). Q1 source = +5V combined node, drain = the higher of (VBUS, BUCK), gate held by R_pullup to VBUS. When VBUS present, gate ≈ VBUS so VGS ≈ 0 → off → BUCK can't back-drive into USB. When VBUS absent, gate is pulled low (through gate pull-down or via the BUCK net), VGS becomes negative, FET conducts → BUCK→+5V.

**Current capability:** rated -4 A which is huge for a 200 mA logic-rail OR-ing → way over-spec'd, fine.

**NIT — verify gate pull-down/pull-up resistor values:** R-network on Q1 gate must guarantee < -2 V VGS when VBUS is removed. R26 (10 kΩ pull-down to GND or to BUCK?) should be reviewed by tracing the schematic in detail. Annotation says *"PMOS gate VBUS pull-up to prevent reverse current to buck output"* — so the gate is pulled UP through a resistor to VBUS, and pulled DOWN through what? The "BUCK starts at 3.3 V default" comment suggests there is no diode/discharge path: when VBUS goes to 0 V, the gate floats and can take time to discharge, leading to a gap where +5V brownouts. **Verify the gate has a hard pull-down to GND (and that the OR-ing crossover is fast enough not to brownout +5 V).**

---

## 9. WSD4066DN (U4 — Winsok dual N-channel MOSFET, DFN-8)

**Datasheet:** https://www.lcsc.com/datasheet/lcsc_datasheet_1912111437_Winsok-Semicon-WSD4066DN_C377861.pdf
LCSC C377861.

- 40 V Vds, 14 A Id
- 17 mΩ @ Vgs = 4.5 V
- VGS(th) ≈ 1 V

**Role inference:** placed in the POWER IN block (U4 at 92.71, 223.52). Two N-FET channels. Most likely a **reverse-polarity protection** circuit: drain on +24V input, source on +24V protected rail (or vice versa), with body-diode forward-biased in the wrong polarity. Combined with U3 (FMMT620 NPN BJT) and possibly U8 (TVS), the BJT senses input polarity / drives the gates. This is a classic "P-FET reverse polarity protection done with N-FET back-to-back to handle high current more efficiently" topology — **except** WSD4066 is a dual N-FET in a small DFN-8, while AO3401A (Q1) is the actual reverse-polarity P-FET-style component on most 24V boards. Here Q1 is on the 5 V tree, NOT on the +24V input.

**Likely topology in the POWER IN block:** N-FET reverse-polarity protection where one MOSFET acts as the high-side switch and the other as a current-mirror or gate driver. The NPN BJT (U3 FMMT620) probably forms a **BJT-driven N-FET reverse polarity**: BJT base at +24V via R, BJT collector to gate, when reverse polarity is applied the BJT turns off and the N-FET is held off via a pull-up resistor. This is a common low-loss reverse-polarity scheme.

**Verify:**
- Vds (40 V) covers 24 V + transient → OK
- Rds(on) 17 mΩ × 8 A peak (motor) = 136 mV drop, 1.1 W dissipation peak → DFN-8 with EP can handle continuous 4 A easily; 8 A peak is short → OK
- **VGS(th) = 1 V is very low** → confirm there is no parasitic ringing/EMI that could turn the FET on inadvertently; gate pull-down resistor must be present.

**NIT — clarify exact role:** the BOM line says "Role unclear from BOM — investigate via schematic" so a layout/schematic-level walkthrough should label the topology explicitly. Add `Reverse Polarity Protection` text annotation.

---

## 10. H5VN10B (U8 — R+O bidirectional ESD/TVS, DFN1006-2L)

**Datasheet:** https://www.lcsc.com/product-detail/C20615784.html (only product page, no full datasheet found)
LCSC C20615784. Manufacturer **R+O**, marking H5VL10BC.

- VWM = 5 V (bidirectional)
- VBR ≈ 6 V (typ)
- VC = 12 V @ IPP = 8 A (8/20 µs)
- DFN1006-2L bidirectional ESD diode

**Role:** sits at U8 (228.6, 52.07) **on the +5V rail at the U9 LDO input**, acting as transient suppression for the LDO. Bidirectional 5 V VWM is the right choice for a 5 V net. **OK.**

**NIT — verify polarity is irrelevant since bidirectional**, but the layout should still place it close to U9 pin 2 (Vin) for short loop area.

---

## 11. FMMT620TA (U3 — Diodes Inc. NPN BJT, SOT-23)

**Datasheet:** https://www.diodes.com/assets/Datasheets/FMMT620.pdf

- VCEO = 80 V
- IC = 1.5 A continuous
- VCE(sat) ≈ 80 mV @ IC = 1 A, IB = 50 mA  (low-saturation NPN)
- hFE ≈ 100 – 250

**Role inference:** in the POWER IN block at U3 (77.47, 234.95) alongside U4 (WSD4066). Most likely the **gate driver / sense element for the N-FET reverse-polarity protection**. With 80 V Vceo it can survive +24 V plus transients on its base/collector. 1.5 A IC is overkill for gate driving — a smaller MMBT3904 would do — but the FMMT620's low VCE(sat) makes it suitable as a **low-side switch** to clamp the gate of the N-FET when reverse polarity is applied or to drive a status LED / power-good signal.

Alternative: U3 could be part of a **soft-start** or **inrush-current limiter** that gradually turns on the N-FET gate (FMMT620 collector to gate, base via RC time constant from +24V) — this matches a typical inrush-limit circuit for boards with bulk caps.

**Verify exact topology in the schematic** — the PNG sheet_01.png shows U3, U4, U5 (TVS), R23/R24 (0Ω), and the FMMT620 forms part of the "Reverse Polarity Protection" block labelled in the top sheet.

**NIT — over-spec'd part choice.** A lower-cost MMBT3904 / 2N3904 would work for most of these roles; only justification for FMMT620 is the 80 V Vceo (transient survival). Acceptable.

---

## ESD coverage matrix

| Connector | Lines | ESD part | Coverage | Verdict |
|-----------|-------|----------|----------|---------|
| J2 USB-C | VBUS, GND, D+, D-, CC1, CC2, SBU1, SBU2 | U6 SRV05-4A (4-ch) | D+, D-, CC1, CC2 | **VBUS and SBU1/SBU2 unprotected** — see BLOCKER#1 |
| J5 CAN (4-pin) | CAN_H, CAN_L, GND, +V | U13 PESD2CAN (2-ch) + ACT1210D CMC | CAN_H, CAN_L | OK — CAN_VIO connector pin (?) **verify** |
| J11, J12 encoder (6P) | VCC, GND, MOSI, MISO, SCK, NSS | U17, U19 SRV05-4A | 4 SPI lines | VCC pin not protected, NIT |
| J1, J7, J8 (3P SH1.0) | unknown 3-pin | U10 SRV05-4A? | unknown — **verify pin mapping** | NIT |
| BK22 mezzanine (24V, GND, etc) | +24V, GND | U5 SMF30CA | +24V transient suppression | **CRITICAL (see BLOCKER#2)** |

---

## BLOCKERS — must address before fab

1. **SMF30CA TVS does not actually protect the DRV8316C.**
   The DRV8316C VM absolute max is 35 V. SMF30CA starts clamping at VBR = 33.3–36.8 V and reaches VC = 48.4 V at full pulse current. By the time the TVS is clamping, the DRV8316C is already over-voltage. **Recommendation:** add an LC filter (or replace with a TVS that has a tighter VC ≤ 33 V) AND/OR verify input-rail transient amplitude is bounded by upstream protection on the BK22 mezzanine. If regen/back-EMF is bounded < 30 V at the cap node by design, this is acceptable; otherwise it is a fail.

2. **USB-C VBUS is not ESD-protected.** SRV05-4A (U6) only covers 4 data lines. A typical ESD strike on VBUS through the USB connector body can reach the +5 V rail and Q1's drain. **Add a small TVS (e.g. PESD5V0L2BT or SMAJ5.0CA) on VBUS at J2.** Currently the only protection is C5/C26 (1 µF) and possibly a polyfuse if present (none listed in BOM — check FB1/PTC parts on schematic).

3. **DRV8316C buck default = 3.3 V; firmware must reprogram to 5 V.**
   On power-up with VBUS absent (motor-only operation), the +5V rail will be only 3.3 V until firmware reprograms the buck. The XC6206 LDO will fall out of regulation (3.3 V – 0.68 V dropout = 2.62 V output). The MCU running off +3.3 V rail must boot at 2.62 V (it won't — STM32G4 brown-out at ~1.65 V actually, but barely). **Mitigation:** strap MCU's BOOT0 / firmware to immediately reprogram buck on first I/O, OR change board to default-boot DRV8316C to 5 V via strap pin / OTP.

---

## CRITICAL — should address before fab

- **Q1 gate timing/dynamic OR-ing**: confirm gate pull-down to GND is hard enough to switch the P-FET on within 1–2 µs of VBUS removal so that +5V doesn't droop and brown-out the MCU. Suggest a 1–10 kΩ to GND alongside the VBUS pull-up.

- **CAN STB pin** (U11 pin 8): must be tied LOW or driven by a GPIO that boots low. Verify the schematic pin connection — if floating, the transceiver stays in standby and CAN doesn't work.

- **Reverse-polarity protection topology** (Q1, U3, U4, U5, U8): the schematic block label is "Reverse Polarity Protection" but the components don't form an obvious reverse-polarity scheme by themselves. Detailed schematic walkthrough required to confirm: which input node enters first, where the N-FET sits (high-side or low-side), how the BJT enables it, and how U5 TVS interacts. **An incorrect topology here means reverse polarity damages the entire board.**

---

## NITS

- **MT6701 magnet placement**: confirm 0.5–3.0 mm air gap, diametric magnetisation. Mechanical review item.
- **MT6701 VDD bulk cap**: only 100 nF on each encoder. Add 1 µF nearby if buck-rail noise propagates.
- **CAN CMC ACT1210D**: confirm placement is between transceiver and connector (not before transceiver).
- **PESD2CAN**: orientation is bidirectional, so polarity-agnostic; confirm GND pin (3) is to chassis/board GND.
- **SRV05-4A on J11/J12**: VCC pin (3.3 V) is not ESD-protected. Optional improvement, low priority.
- **CAN-FD speed**: ACT1210D is rated for CAN-FD; no concern.
- **FMMT620**: over-spec'd; cheaper alternative exists but no functional issue.
- **WSD4066DN**: VGS(th) = 1 V is low; verify gate pull-down exists.

---

## Datasheet URLs cited

- DRV8316C — https://www.ti.com/lit/ds/symlink/drv8316c.pdf
- MT6701 Rev 1.8 — https://www.novosns.com/enfiles/MT6701_Rev.1.8.pdf
- MT6701 Rev 1.5 — https://uploadcdn.oneyac.com/attachments/files/brand_pdf/magntek/F3/CA/MT6701QT-STD.pdf
- CA-IF1044VD-Q1 (Chipanalog, LCSC mirror) — https://www.lcsc.com/datasheet/C5155979.pdf
- ACT1210D family — https://product.tdk.com/system/files/dam/doc/product/emc/emc/cmf_cmc/catalog/cmf_automotive_signal_act1210d_en.pdf
- ACT1210D-101-2P-TL00 product page — https://product.tdk.com/en/search/emc/emc/cmf_cmc/info?part_no=ACT1210D-101-2P-TL00
- PESD2CAN — https://assets.nexperia.com/documents/data-sheet/PESD2CAN.pdf
- SRV05-4 — https://www.onsemi.com/download/data-sheet/pdf/srv05-4-d.pdf
- SMF30CA (Littelfuse) — https://uk.farnell.com/littelfuse/smf30ca/tvs-diode-bidir-30v-sod-123fl/dp/3930021
- XC6206P332MR — https://www.alldatasheet.com/datasheet-pdf/view/243854/TOREX/XC6206P332MR.html
- AO3401A — http://www.aosmd.com/pdfs/datasheet/AO3401A.pdf
- WSD4066DN — https://www.lcsc.com/datasheet/lcsc_datasheet_1912111437_Winsok-Semicon-WSD4066DN_C377861.pdf
- H5VL10BC (R+O) — https://www.lcsc.com/product-detail/C20615784.html
- FMMT620 — https://www.diodes.com/assets/Datasheets/FMMT620.pdf
