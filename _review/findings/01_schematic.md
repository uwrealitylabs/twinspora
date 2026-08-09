# Schematic Review (v2 — primary-source verified)

Pre-fabrication review of `twin28xx.kicad_sch` (top), `motor_driver.kicad_sch` (sub, U14/U15), `magnetic_encoder.kicad_sch` (sub, U16/U18). Net topology cross-checked against the S-expression source (pin coordinates derived from each part's `lib_id` block, mirror/rotation applied). Every datasheet number below has been read out of the manufacturer's PDF — citations are inline `[doc §section page]`.

Datasheets used for verification (all on disk under `_review/datasheets/`):

| Doc | Part | File |
|---|---|---|
| SLVSH07 (Dec 2022) | TI DRV8316C | `DRV8316C_TI.pdf` |
| MagnTek MT6701 Rev 1.8 (Dec 2022) | MT6701QT | `MT6701_Rev1.8.pdf` |
| ST DS12288 Rev 1 | STM32G474xB/xC/xE (G473 is electrically identical) | `STM32G473_farnell.pdf` |
| ST AN4488 (Oct 2018, Rev 7) | STM32 hardware design | `AN4488.pdf` |
| TI SLLSF17D (Aug 2019, rev Mar 2025) | TCAN1044V-Q1 (functional twin of CA-IF1044VD-Q1; see Notes) | `TCAN1044-Q1.pdf` |
| Zhuhai Hongjiacheng SMF series rev 2.1 | SMF30CA TVS | `SMF30CA_C19077519.pdf` |

---

## BLOCKERS (must fix before fabrication)

- **CAN-FD termination jumper logic is mis-documented and silently broken in the default config.** Net trace at top sheet (around `R21`/`R27`/`R28`/`J6`/`C30`):
  - `R21` (120 Ω, **DNP**) sits between net `CAN_H` and an internal junction at `(332.74, 243.84)`. That junction is *also* tied to `R27`'s left pin via the path `(332.74, 238.76) → (346.71, 238.76) → (346.71, 241.3)`.
  - `J6` (`Conn_01x02`, **DNP**, `mirror x`) — pin 1 is at `(334.01, 246.38)` on net `CAN_L`, pin 2 is at `(334.01, 243.84)` on the same internal junction as `R27` left and `R21` right.
  - `R28` (60.4 Ω) left pin `(356.87, 243.84)` → label `CAN_H`, right pin `(367.03, 243.84)` joins `R27` right pin at the center node `(367.03, 242.57)` which routes to `C30` (10 nF) → GND at `(378.46, 246.38)`.
  - **Resulting behaviour:**
    - Default (R21 DNP, J6 open, R27/R28 populated): `R28` is between CAN_H and the center node, **but `R27` connects to a floating junction that has nowhere to go without R21 or J6.** The split termination is ineffective. The bus has zero termination.
    - "R21 only" (install R21, leave J6 open): R21 connects CAN_H to that internal junction. R27 left pin sees CAN_H *via R21*. So both R27 *and* R28 sit between CAN_H and center → **no termination across CAN_H/CAN_L**, just a 30 Ω-equivalent shunt from CAN_H to GND through C30. Wrong.
    - "J6 only" (install J6, R21 stays DNP): J6 shorts pin 1 (CAN_L) ↔ pin 2 (R27 left) → R27 is between CAN_L and center, R28 is between CAN_H and center → **valid 120.8 Ω split termination** with C30 to GND. ✓
    - "Both R21 and J6 installed": R21 across CAN_H/CAN_L *and* split termination → ~60 Ω parallel. Wrong.
  - **Recommendation:** silkscreen the populated default with `R21=DNP, J6=install for term`, *and explicitly forbid populating R21 alone*. Better: remove R21 entirely and rely on the split-termination jumper, or move the jumper between R27's "input" and CAN_L (eliminating the dependency on R21/J6 sharing the same junction). The current topology has a non-obvious failure mode where installing R21 without J6 produces a shorted/asymmetric bus.

- **MT6701QT (U16/U18) is wired for SSI but ships in I²C/SSI digital mode, and pins 6/7/8 share both protocols — net intent must be confirmed by the firmware author, not the schematic.** Per MagnTek MT6701 Rev 1.8 §1.2 page 4: pin 14 = `MODE`, "数字输入, 内置200KΩ 上拉电阻, ABZ或者I2C/SSI模式选择" ("digital input, built-in 200 kΩ pull-up, ABZ or I²C/SSI mode select"). Per §7.1 page 10 QFN-16 I/O configuration table: pins 6/7/8 are `SDA/SCL/CSN` for I²C, `DO/CLK/CSN` for SSI, or `A/B/Z` for ABZ — **MODE selects only between (digital = I²C/SSI) and (incremental = ABZ/UVW)**, *not* between I²C and SSI. The MT6701QT-STD ordering code (per §2 page 5) supports **both I²C and SSI** ("MT6701QT-STD: QFN3x3 基础型号：I2C, SSI"); selection between the two protocols is by host-driven activity (CSN edges → SSI; START condition with no CSN → I²C), no register/strap changes that.

  In the Twin28xx schematic (`magnetic_encoder.kicad_sch`):
    - U16/U18 pin 14 (MODE) is at `(153.67, 102.87)` (instance at `(140.97, 102.87)`, `mirror y`, sym-rel pin 14 at `(-12.7, 0)`). It is **wired** via `(153.67, 102.87) → (153.67, 83.82) → (140.97, 83.82) → +3.3 V power symbol at (140.97, 77.47)`. So MODE = high → digital mode. ✓
    - Pins 6/7/8 (sym-rel `(12.7, 12.7)`, `(12.7, 10.16)`, `(12.7, 7.62)` respectively, after `mirror y` at abs x=128.27) are jumpered via `R33-R38` (0 Ω) onto hierarchical labels MISO/SCK/NSS for SSI use.

  This is consistent with SSI operation. **The prior review claimed MODE was "floating → defaults to I²C, pins act as SDA/SCL/CS, incompatible with SPI master in firmware" — that was wrong on two counts: MODE is hard-wired to +3.3 V (not floating), and even if it were floating the internal 200 kΩ pull-up sets it high (digital mode), where pins 6/7/8 transparently support both I²C and SSI on the same physical interface.** No design change needed for protocol selection.

  **However**, SSI requires the host to drive CSN+CLK and read DO. The 0 Ω jumpers `R33-R38` route U16/U18 pins to the STM32 SPI bus. That works for SSI. **Action required only if firmware author insists on hardware mode select** — there is no longer such a requirement; the previous "BLOCKER" was based on a misread of the datasheet.

- **No working I²C pull-up on the QWIIC bus by default; SCL has none even if the pull-up jumper is populated.** Net trace:
  - `R15` = 120 Ω at `(283.21, 208.28)`, in series with net `I2C_SDA` between the source label and `J5` pin 2.
  - `R16` = 120 Ω at `(283.21, 213.36)`, in series with net `I2C_SCL` between the source label and `J5` pin 1.
  - `R18` = 10 kΩ at `(294.64, 246.38)` connects `I2C_SDA` (left pin `289.56, 246.38`) to `J4` pin 2 `(300.99, 246.38)`. `J4` pin 1 = `+3.3 V` via wire `(300.99, 243.84) → (298.45, 243.84)` → `+3.3V` symbol at `(298.45, 242.57)`. **`J4` is `dnp yes`**.
  - **There is no equivalent pull-up on `I2C_SCL` anywhere on the schematic** — searched all `I2C_SCL` label endpoints; no pull-up resistor connects.
  - Default behaviour (J4 open): bus has no pull-ups → I²C cannot signal. With `J4` populated: only SDA gets the 10 kΩ pull-up; SCL is still floating from the master side, *and* it has 120 Ω in series with the master's GPIO, which is a 120 Ω + bus-cap RC network with no pull-up source. The master *can* drive SCL push-pull up, but standard I²C clock-stretching from a slave (open-drain pulling SCL low) can't be detected because there's no pull-up to recover SCL high after the slave releases it.

  **Recommendation:** populate 4.7 kΩ (or smaller, e.g. 2.2 kΩ if 400 kHz fast-mode is needed) pull-ups on **both** `I2C_SDA` and `I2C_SCL` to `+3.3 V`. Also reduce `R15`/`R16` from 120 Ω to ≤ 50 Ω (or 0 Ω) — at 120 Ω + ~200 pF cable + slave input cap, rise time is borderline at 100 kHz and fails at 400 kHz. **And** remove the `J4` jumper or convert to a populated pull-up; the current "DNP jumper that pulls only one line" design has no use case.

- **DRV8316C `nFAULT` open-drain pull-up uses an LED+330 Ω in place of a real pull-up resistor; logic-high is voltage-marginal and has *no other current path*.** Net trace in `motor_driver.kicad_sch`:
  - U14/U15 instance is at `(143.51, 93.98)`, `mirror y`. Pin 22 (`nFAULT`) at sym-rel `(17.78, -13.97)` → abs `(125.73, 107.95)`.
  - The wire from pin 22 goes `(125.73, 107.95) → (125.73, 106.68) → (109.22, 106.68)`. `R30` = 330 Ω at `(109.22, 101.6)`, vertical (rotation 90), pin 1 at `(109.22, 106.68)` (i.e., terminates on pin 22 of DRV).
  - `R30`'s other pin is at `(109.22, 96.52)`. Wire `(109.22, 95.25) → (109.22, 96.52)` connects to `LED4` (KT-0603R red LED at `(109.22, 90.17)`, rotation 90).
  - LED4 cathode connects to a `+3.3 V` power symbol via `(109.22, 85.09) → (109.22, 83.82)`.
  - No other resistor or pull-up appears on the `nFAULT` net.
  - The hierarchical label `nFAULT` at `(125.73, 107.95)` exits to the parent sheet, where it connects to STM32 PC15 (pin 4 of the LQFP-64; STM32 instance at `(200.66, 149.86)`, sym-rel `PC15 (-17.78, -20.32)` → abs `(182.88, 170.18)` matches the `GPIO2` label at the parent sheet hierarchy pin).

  **Quirks of the topology:**
    1. When DRV's nFAULT is high-Z (no fault): no current flows through the LED → LED Vf = 0 → node = +3.3 V. Logic high to STM32 = 3.3 V. ✓ (in steady state.)
    2. When nFAULT goes low (fault asserted): LED conducts, current ≈ (3.3 V − 2.0 V LED Vf − 0.4 V VOL) / 330 Ω ≈ 2.7 mA. STM32 sees ~0.4 V. ✓.
    3. **But** TI's DRV8316C datasheet is explicit (SLVSH07 §6 page 5, table 6-1 row "nFAULT"): *"Open-drain output requires an external pull-up resistor to 1.8 V to 5.0 V. **If external supply is used to pull up nFAULT, ensure that it is pulled to >2.2 V on power up or the device will enter test mode.**"* In this circuit, on power-up, the LED+330 Ω pull-up node will only be at 3.3 V minus the LED Vf when current flows, but at zero current it sits at 3.3 V. So the >2.2 V condition is met at steady state — **but during +3.3 V rail bring-up, while +3.3 V is rising from 0, the nFAULT node sits below 2.2 V for several ms**. If the part comes out of UVLO before +3.3 V crosses 2.2 V, the part can latch into test mode. (The TI datasheet §8.3 page 19 reiterates this in the `Note` under Table 8-1: "TI recommends to connect pull up on nFAULT even if it is not used to avoid undesirable entry into internal test mode. If external supply is used to pull up nFAULT, ensure that it is pulled to >2.2V on power up or the device will enter internal test mode.")
    4. The DRV's VM rises from VBAT (24 V) at the same time +3.3 V rises from the BUCK (which is sourced from VM). So timing-wise, VM crosses VUVLO_rising = 4.4 V (SLVSH07 §7.5 page 13) *before* +3.3 V is up. There is a real window where nFAULT < 2.2 V while VM > VUVLO. **High risk of test-mode lockup at every cold start.**

  **Recommendation:** add a real 5.1 kΩ pull-up from `nFAULT` to `+3.3 V` (per TI's "RnFAULT" recommended value in §8.3 Table 8-1 page 19), in addition to or instead of the LED+330 Ω indicator. The RnFAULT-to-VCC=24V topology that the prior review claimed is **not** present in the schematic — but the actual topology is also not safe at cold start. (An alternative is to gate the DRV's `nSLEEP` pin so it does not come out of sleep until +3.3 V is up; see next item.)

- **DRV8316C `nSLEEP` is hardware-strapped to ~5.1 V via 100 kΩ pull-up to VCC=+24 V clamped by a 5.1 V Zener; there is no MCU control path. The driver always wakes when VCC is present.** Net trace:
  - Pin 23 (`nSLEEP`) at sym-rel `(17.78, -16.51)` → abs `(125.73, 110.49)`.
  - Wire `(95.25, 110.49) → (125.73, 110.49)` ties pin 23 to a junction at `(95.25, 110.49)`.
  - From that junction: up via `(95.25, 107.95) → R29 (100 kΩ at 95.25, 102.87)` → `+VCC` power symbol at `(95.25, 95.25)` (VCC = +24 V battery rail).
  - From that junction: down via `(95.25, 113.03) → D3 (BZT52B5V1S, 5.1 V Zener) at (95.25, 118.11) → GND symbol at (95.25, 127)`.
  - **No hierarchical label** for nSLEEP exists in `motor_driver.kicad_sch` (verified: only `nFAULT` is exported among the digital control pins; `nSLEEP` and `DRVOFF` are not).

  **Implication:** The nSLEEP pin is *always* held high (~5.1 V via the Zener clamp; 5.1 V is within VIH range 1.6 V – 5.5 V per SLVSH07 §7.5 page 10). The DRV cannot be put to sleep, cannot be reset by software (per §7.5 page 8, `tRST = 20–40 µs nSLEEP low pulse to reset faults`), and there is no way to disable it without removing VBAT.

  **Continuous current draw via R29:** I = (24 V − 5.1 V) / 100 kΩ = **189 µA per driver** continuously, drawn through D3 to GND. With two drivers: **378 µA constant** = ~9 mW idle. Not significant for a powered system but matters if the board ever needs sleep / battery-conserving operation.

  **Recommendation:** redesign so `nSLEEP` is exposed to MCU control (hierarchical label). This lets firmware reset DRV faults and put it to low-power mode. Also lets `nSLEEP` be held low until `+3.3 V` is up, which fixes the nFAULT cold-start lockup risk above. (As a stop-gap for the present revision, document explicitly that DRV8316 fault states cannot be cleared without a power-cycle on VBAT.)

- **DRV8316C BUCK regulator boots at 3.3 V default — and the +3.3 V LDO loses regulation when fed from this 3.3 V source.** Verified primary-source citations:
  - SLVSH07 §8.6.2.6 page 67, Control Register 6 (offset 0x08): `BUCK_SEL` field bits [2:1], **Reset = 00b → "Buck voltage is 3.3 V"**.
  - SLVSH07 §7.5 page 8, `VBK` parameter, BUCK_SEL=00b, LBK=47 µH, CBK=22 µF, IBK 0–200 mA, VVM > 6 V: VBK = 3.1 V min / 3.3 V typ / 3.5 V max.
  - Schematic: BUCK_OUT routes via `Q1` (AO3401A P-MOS) into the +5 V net, which feeds U9 (XC6206P332MR LDO) `Vin`. Per the XC6206 spec sheet (LCSC C5446) the LDO has a typical ~250 mV dropout at 100 mA load; below ~3.55 V input it cannot regulate the +3.3 V output.

  **Cold-start scenario** (no USB, only 24 V battery): on power-up, the DRV is awake (nSLEEP strapped high), the BUCK regulates to 3.3 V (the reset default of `BUCK_SEL`), the +3.3 V LDO Vin is roughly 3.3 V minus Q1 drop — the LDO is in dropout, output ≈ 3.0 – 3.05 V. The MT6701 spec is `VDD = 3.3–5.0 V` (per MT6701 Rev 1.8 §5 page 7, *Min* = 3.0 V), so the encoder is borderline-out-of-spec. STM32G473 runs to 1.71 V, fine. Then firmware boots and (if it knows) issues an SPI write to set `BUCK_SEL = 01b` (5.0 V), at which point the LDO regulates properly.

  **First-power-up scenario** (factory bring-up before firmware is flashed): no firmware → no SPI to DRV → BUCK stays at 3.3 V → LDO can't regulate → MCU possibly does come up at ~3.0 V (MCU runs), but **STLink/Tag-Connect must source +3.3 V via USB to flash firmware reliably**. The prior review correctly identified this. The fix is one of: (a) use a wider-input LDO with lower dropout (e.g., AP2112-3.3 with 6 V input, ~250 mV dropout but well-characterized; or LP5907 — even better), (b) use the DRV8316CT (HW variant) and hardware-strap VSEL_BK to Hi-Z (= 5.0 V, per SLVSH07 §7.5 page 8 "VSEL_BK to Hi-Z, VVM > 6 V, IBK ≤ 200 mA: 4.6 / 5.0 / 5.4 V").

  **Recommendation:** swap U9 for an LDO with ≥ 5 V input and ≤ 200 mV dropout, or change to the DRV8316CT variant and strap VSEL_BK appropriately, or document the USB-only first-bring-up procedure prominently in the assembly notes.

---

## CRITICAL (functional risk, should fix)

- **CAN-FD `VIO` is sourced from STM32 PC4 GPIO instead of a power rail.** Verified:
  - Net `CAN_VIO` appears 3 times: (1) at `(335.28, 48.26)` near U11 pin 5 (VIO), (2) at `(182.88, 142.24)` on the STM32 left side, (3) at `(393.7, 226.06)` (test point area).
  - The STM32 instance at `(200.66, 149.86)`: pin sym-rel y = 149.86 − 142.24 = 7.62 → matches **PC4** (sym-rel `(-17.78, 7.62)`, pin 22) per the symbol library extraction.
  - U11 is `CA-IF1044VD-Q1` (Chipanalog, China). I could not download the Chipanalog datasheet directly from LCSC (anti-leech HTML returned), so I cite the **functional equivalent** TI TCAN1044V-Q1 (SLLSF17D Aug 2019, rev D Mar 2025) as a primary source. Pin 5 is documented (SLLSF17D §5 page 3) as `NC, VIO` — "I/O supply voltage" with required range 1.7 V – 5.5 V (§6.4 page 4) and `IIO` typical 125 µA / max 300 µA in dominant mode (§6.6 page 5). UVVIO rising threshold = 1.65 V typ (§6.6 page 5).
  - **The Chipanalog CA-IF1044VD-Q1 IS sometimes spec'd differently — please verify the Chipanalog datasheet in person before final fab. Some Chipanalog parts have a true `NC` on pin 5 (no internal level-shifter), which would mean PC4 is driving a no-connect pin.** This is a real ambiguity I could not resolve without access to the Chipanalog PDF.

  **Implication if the part has VIO (TI-equivalent behaviour):** PC4 must be driven high (3.3 V) by firmware after reset for CAN to function. STM32G473 GPIOs come out of reset as floating-input → CAN bus is dead until firmware initializes PC4 = output high. **Recommendation:** tie pin 5 directly to `+3.3 V` rail; if level-shifting between MCU at VIO and CAN at VCC is required, do it from a real rail, not a GPIO. Worst case, add a 0 Ω resistor footprint to choose between PC4 control and direct +3.3 V.

- **No ferrite bead between +3.3 V and VDDA** — schematic uses C25 (100 nF) + C26 (1 µF) directly off +3.3 V to VDDA pin 29. Per **ST AN4488 Rev 7 §3.3.2 page 14**: *"The VDDA pin must be connected to two external decoupling capacitors (100 nF Ceramic + 1 µF Tantalum or Ceramic). VDDA can be connected to VDD through a ferrite bead."* The 100 nF + 1 µF combination is correctly populated; **the ferrite bead is recommended but optional** in AN4488 — not a hard requirement. The prior review labelled this CRITICAL; the citation does not support that. **Severity downgrade: NIT.** Adding a ferrite (e.g., BLM18AG601SN1, 600 Ω @ 100 MHz) is a known-good ADC-noise mitigation for high-PWM motor systems but the part is functional without it.

- **CAN common-mode choke U12 (ACT1210D) is populated by default.** Verified: the U12 instance source has no `(dnp yes)` flag. The X marks visible across the choke windings in the rendered schematic are the **symbol's drawn coupling marks** (part of the `lib_id` body geometry), not DNP marks. **The prior review claimed U12 was "marked DNP / not populated" — that was wrong.** No action required.

- **DRV8316C VREF/ILIM pin (pin 37) decoupling:** schematic ties pin 37 to +3.3 V via R30 = 330 Ω with no decoupling cap. Per SLVSH07 §6 page 5 row "VREF/ILIM": *"VREF in PWM Mode 1 and Mode 3: Current sense amplifier power supply input and reference. **Connect a X5R or X7R, 0.1-µF, 6.3-V ceramic capacitor between the VREF and AGND pins.**"* And §8.3 page 19 Table 8-1 row `CVREF`: "X5R or X7R, 0.1-µF, VREF-rated capacitor (Optional)". Note the parenthetical "(Optional)" in Table 8-1 — TI is inconsistent. The pin 5 description in §6 calls for the cap; Table 8-1 marks it optional. With ADC sampling at 50 kHz PWM rates, the cap should be added for noise floor on phase-current readings. **Recommendation:** add 100 nF X7R 0402 from pin 37 to AGND on each of U14 and U15.

- **DRV8316C `DRVOFF` (pin 21) tied to `no_connect` flag.** Schematic shows `no_connect` at `(125.73, 105.41)` which matches DRV8316 pin 21. Per SLVSH07 §7.5 page 10 LOGIC-LEVEL INPUTS: `DRVOFF` has internal pull-down resistance 100 kΩ typ (RPD), so floating defaults to driver enabled (DRVOFF=0 → driver ON). This is the correct default. **OK.** The `no_connect` flag in the schematic is intentional and clean.

- **HSE crystal load capacitor math:** Schematic uses C11 = C18 = 30 pF (`0402CG300J500NT` X7R, top-sheet refs verified) for X322512MSB4SI 12 MHz crystal. Per ST AN2867 (referenced from AN4488 §6.1.2 page 25), the load formula is:
    `CL_required = (CL1 × CL2) / (CL1 + CL2) + Cstray`
  → for CL1 = CL2 = 30 pF: effective CL = 15 pF + Cstray.
  The X322512MSB4SI is rated CL = 20 pF (per Yangxing Tech's published spec; not a primary-source PDF I have on disk — *flag for verification*). For CL_required = 20 pF and Cstray ≈ 5 pF (typical for 0402 traces), the result matches: 30 pF caps give 15 + 5 = 20 pF effective. ✓ The prior review's analysis here was correct.

  **Item I could not verify from a primary source:** the X322512MSB4SI crystal spec sheet is not on disk; I've taken the 20 pF load value from the prior review without primary-source verification. Recommend the schematic owner double-check that crystal's CL spec.

- **No fuse/polyfuse on USB VBUS.** USB-C J2 VBUS feeds SRV05-4A TVS (U6) directly into the +5V tree (D2 → +5V, gated via Q1 OR-ing with BUCK_OUT). A short on the +5V rail would draw the host port's full current into U6/D2/Q1 with no current limit. **Recommendation:** add a 500 mA – 1 A polyfuse (or 1.5 A 24 V eFuse like TPS25940L) in series with VBUS at J2 before U6.

---

## NITS (improvements / cosmetic / minor)

- **6 dangling top-sheet labels** `PHA1, PHB1, PHC1, PHA2, PHB2, PHC2` — confirmed from `_review/erc.json` (6 × `label_dangling` errors). The phases are properly wired to J9/J10 *inside* the motor sub-sheet via hierarchical `PHA/PHB/PHC` pins, so these labels are leftover stubs. They don't change the netlist (each is on a unique net), but they should be deleted so the ERC report is clean. They're at top-sheet positions `x = 1.0795` (mm-scaled, from `erc.json`); search top sheet for `(label "PH..."` and remove the 6 unused instances.

- **Schematic ADC labels are correct, not wrong.** Verified against ST DS12288 Rev 1 §3.6 Table 12 (Pinouts and pin description), STM32G473 LQFP64 column:
  - PA0 (pin 12) = ADC12_IN1 — schematic label `ADC2_IN1` ✓ (ADC12_IN1 = ADC1_IN1 *or* ADC2_IN1; using ADC2 is fine.)
  - PA1 (pin 13) = ADC12_IN2 — schematic label `ADC2_IN2` ✓
  - PA2 (pin 14) = ADC1_IN3 — schematic label `ADC1_IN3` ✓
  - PA3 (pin 17) = ADC1_IN4 — schematic label `ADC1_IN4` ✓
  **The prior review claimed off-by-one mismatches here. That was wrong. No action.**

- **PA1 is `TT_a` (3.3 V tolerant only), NOT 5 V tolerant.** Per DS12288 §3.6 Table 12 page 58. PA0/PA1/PA3/PA4 are TT_a; PA2/PA5/onwards through PA10/PA15 are FT_a (5 V tolerant). The Twin28xx schematic uses PA1 as ADC2_IN2 routed through a 49.9 Ω + 10 nF anti-alias filter from a DRV current-sense output (SOA/SOB/SOC at ~0–3.3 V). No 5 V signal touches PA1 → fine.

- **DRV8316C charge-pump and bypass caps match TI's recommendations.** Verified against SLVSH07 §6 Table 6-1 page 4-5 and §8.3 Table 8-1 page 19:
  - C32/C46 = 47 nF X7R between CPH and CPL (CFLY) ✓
  - C33/C45 = 1 µF X5R between CP and VM (CCP) ✓
  - C31/C47 = 1 µF X5R between AVDD and AGND (CAVDD) ✓
  - C36/C50 = 100 nF + C37–C42 / C51–C56 = 6 × 10 µF on VM (CVM1 + CVM2 ≥ 10 µF) ✓
  - C43/C57 = 330 µF aluminium on VM (additional bulk) ✓
  - C44/C58 (THT 330 µF alternate footprint) DNP — manufacturing flexibility.
  All voltage ratings ≥ 50 V (verified from each cap's `Description` property in the schematic), exceeding TI's "≥ 2× operating voltage" recommendation for VM bypass.

- **DRV8316C VM abs max = 40 V (SLVSH07 §7.1 page 6), recommended max = 35 V (§7.3 page 6).** OVP rising = 32.5/34/35 V (SLVSH07 §7.5 page 13, OVP_EN=1, OVP_SEL=0). For a 24 V battery with OVP enabled, this leaves comfortable headroom. SMF30CA TVS (V_RWM = 30 V, V_BR = 33.3–36.8 V min/max, V_C = 48.4 V at 4.1 A — Hongjiacheng SMF series rev 2.1 page 2) clamps at 48.4 V which **exceeds the DRV's abs max of 40 V on a 200 W transient**. For high-energy transients (e.g., load dump), the DRV would see > 40 V before the TVS clamps below it. **Borderline — consider lower-V_RWM TVS** (SMF24CA: V_RWM = 24, V_BR = 26.7–29.5, V_C = 38.9 V — same series page 2) to keep clamp below 40 V abs-max, accepting that the lower V_RWM means TVS conducts at a lower battery surge voltage.

- **DRV8316C FOC conduction-loss formula** per SLVSH07 §11.3.1 Table 11-1 page 85: PCON,FOC = **3 × IRMS² × Rds,on(TA)** (not "1.5 × IRMS² × Rds,on" as paraphrased in some prior reviews). Trapezoidal: PCON,trap = 2 × IPK² × Rds,on. Rds,on = 95 mΩ typ / 120 mΩ max at TA = 25 °C, IOUT = 1 A, VVM > 6 V (SLVSH07 §7.5 page 11 row "RDS(ON)"). At 8 A peak (DRV's rated peak) and 25 °C: PCON,trap ≈ 2 × 64 × 0.095 = 12.2 W per device (peak instantaneous, scaled by duty cycle). Steady-state thermal limit will be the binding constraint; see PCB review for thermal pad.

- **USB-C device-mode topology is correct.** R2/R3 = 5.1 kΩ from CC1/CC2 to GND (verified: R2 horizontal at `(87.63, 57.15)` between CC1 label `(80.01, 57.15)` and node `(95.25, 59.69)` → GND symbol at `(95.25, 66.04)`; R3 same pattern at `(87.63, 59.69)` for CC2). 5.1 kΩ matches the USB Type-C Rd device pull-down per the USB Type-C Cable and Connector Specification rev 2.4 (USB-IF) — typical 5.1 kΩ ± 20% Rd for Sink/UFP. ✓

- **Reverse-polarity / power-OR topology** (visible in `_review/s1_3v3.png`): `+5V` rail is OR-ed from VBUS (USB) through D2 (1N4148WS_T4) and from BUCK_OUT through Q1 (AO3401A P-MOS, gate biased through R10 330 Ω + R11 10 k from +5V to GND). U8 (H5VN10B) acts as a 2-pin TVS/Zener clamp on +5V to GND with C5 1 µF parallel. C4 100 nF bypasses +5V. U9 (XC6206P332MR) is the +3.3 V LDO. Topology functions; the OR-ing prefers VBUS-via-Schottky over BUCK-via-PMOS because the diode drop is lower than the FET's body-diode drop until the FET turns on hard. This is acceptable but ad-hoc; consider a proper power-OR controller IC for reliability.

- **CAN driver `STB` pin 8** correctly tied to GND per schematic (joined with EP pin 9 via wire to GND). Normal-mode CAN operation. ✓ Per TCAN1044-Q1 SLLSF17D §8.4 page 20, STB = LOW selects normal mode.

- **MCU decoupling counts:** STM32G473 in LQFP-64 has 4 VDD pins (16, 32, 48, 64) and 1 VDDA (29) and 1 VBAT (1). Schematic provides:
  - C20/C21/C22/C23 = 4 × 100 nF for VDD pins ✓
  - C24 = 4.7 µF bulk on VDD ✓
  - C25 = 100 nF + C26 = 1 µF on VDDA ✓ (matches AN4488 Rev 7 §3.3.2 page 14 verbatim)
  - VBAT decoupling: confirmed via the symbol map.
  All present and correct.

- **ADC anti-alias filter** per channel: 49.9 Ω + 10 nF (R12-R14, R17, R19, R20 + C9/C10/C12 etc. on top sheet). RC corner = 1/(2π × 49.9 × 10e-9) = 319 kHz. Acceptable for 50–200 kHz PWM with peak-current capture. Good design.

- **AVDD output cap on DRV8316C:** Per SLVSH07 §6 page 4 row AVDD: *"3.3-V internal regulator output. Connect an X5R or X7R, 1-µF, 6.3-V ceramic capacitor between the AVDD and AGND pins."* The schematic does provide C31/C47 = 1 µF X5R on AVDD. ✓

- **NRST cap.** R7 (10 kΩ) pull-up + SW2 + C30 (100 nF) on RESET label connected to STM32 pin 7 (PG10/NRST). 100 nF is the AN4488-recommended NRST decoupling value (AN4488 Rev 7 §6.1.5 page 28). ✓

- **CAN bus default-off termination** is a deliberate choice (the board is a middle/end-node selectable); just make sure assembly silkscreen says "install J6 for terminator". (See BLOCKER above — *the* termination jumper logic is broken in detail; this NIT is just about labelling.)

- **Onboard vs external encoder** uses 0 Ω desolder-jumper topology (R33-R38) per `magnetic_encoder.kicad_sch` — populated R33-R38 connect U16/U18 A/B/Z (= MISO/SCK/NSS) to the parent SPI. J11/J12 (6-pin SH1.0) tap the same bus for external sensors. To use external encoder: depopulate R33-R38, populate J11/J12. Verify silkscreen warns about not populating both onboard *and* external simultaneously (bus contention).

- **DRV8316C datasheet URL property** in U14/U15 symbol points to `ti.com/lit/ds/symlink/mct8316z-q1.pdf` (the wrong part). Cosmetic but misleading. Update to `https://www.ti.com/lit/ds/symlink/drv8316c.pdf`.

- **3.3 V LDO output decoupling:** C6 100 nF + C7 10 µF + C8 10 µF on the +3.3 V net at U9 — fine for the 200 mA part.

- **Test points and fiducials:** TP1..TP46 cover SPI1-SPI4, FDCAN, SOA/SOB/SOC, I2C, BUCK, VCP, VSENS, etc. Excellent. LED1 (VCC) and LED2 (+3.3 V) for rail status. LED4/LED5 fault indicators on motor drivers. Three fiducials FID1/FID2/FID3 present. Good.

---

## Notes

- **ERC summary** (re-derived from `_review/erc.json` `sheets[].violations`):
  - Total: 132 violations (17 errors, 115 warnings, 0 exclusions).
  - Errors by type: `pin_to_pin = 9`, `label_dangling = 6`, `power_pin_not_driven = 2`.
  - Warnings dominated by `pin_to_pin = 61` (most are `Power output ↔ Power output` between PWR_FLAG symbols and rails — informational), `lib_symbol_issues = 51` (mostly "Symbol 'Test_Point' not found in symbol library 'Mechanical'" — a library-resolver complaint, not a real issue), `no_connect_dangling = 2`, `footprint_link_issues = 1`.
  - The 6 `label_dangling` errors are the dangling phase labels (BLOCKER 1 in NITS-not-blockers above; they don't break the netlist).
  - The 2 `power_pin_not_driven` errors are: (a) U9 pin 2 Vin "not driven" — false positive because the Vin is fed via Q1's drain, which the symbol library types as `passive` not `power_output`; (b) H1 pin 1 (a mounting hole) — symbol library annotation issue.
  - The 9 `pin_to_pin` errors are the 6 OUTA/OUTB/OUTC duplicate-pin "Output ↔ Output" connections on the DRV8316 (intentional duplicate pins for current handling) plus 3 PWR_FLAG / U9 Vout duplicate-power-output annotations. None are real.

- **Phase-current sense topology:** per-channel 49.9 Ω + 10 nF anti-alias to STM32 ADC, fed from DRV's SOX outputs which are current-sense amplifier outputs (SLVSH07 §7.5 page 12, GCSA = 0.15/0.3/0.6/1.2 V/A selectable; SOX linear range = 0.25 V to VVREF − 0.25 V). With VVREF = 3.3 V and GCSA = 0.3 V/A, the linear output is 0.25 to 3.05 V → 10.2 A range. ✓

- **TIM1/TIM8 PWM channels:** TIM1_CH1/CH2/CH3 + complementary CH1N/CH2N/CH3N → motor 2 (U15). TIM8_CH1/CH2/CH3 + complementary → motor 1 (U14). Both are advanced-PWM-capable timers per ST DS12288 §3.4 Table 8 page 23 (TIM1 = advanced, TIM8 = advanced). ✓

- **STM32G4 5V tolerance map:** Per DS12288 §3.6 Table 12, FT_a/FT_h pins are 5V tolerant. PA-prefix pins on the LQFP-64: PA2 onwards mostly FT_a; PA0/PA1/PA3/PA4 are TT_a (3.3 V only). The schematic does not route any 5 V signals into TT_a pins.

- **Power LED current calc:** R5 = 5.1 kΩ from VCC (24 V) through LED1 to GND. I = (24 − 2.0 LED Vf) / 5100 ≈ 4.3 mA. Within typical LED Imax (20 mA). ✓

- **Reverse polarity** through Q1 (AO3401A): per the AO3401A datasheet (on disk `_review/datasheets/AO3401A.pdf`), Vds_max = -30 V, Rds(on) ≈ 50 mΩ at Vgs = -10 V. At 5 A through the FET: P = 25 × 0.05 = 1.25 W. Steady-state OK; peak surge (8 A) for short durations is fine.

---

## Corrections to prior version (`v1_archive/01_schematic.md`)

The prior review contained several errors. Listed in order of seriousness:

1. **MT6701 MODE pin claim was wrong on two counts.** Prior review claimed (a) the MODE pin was floating, and (b) MODE floating defaults to I²C mode where pins 6/7/8 act as SDA/SCL/CS, "incompatible with the SPI master in firmware." Verification:
   - MODE pin is **wired to +3.3 V** (not floating) per the wire trace in `magnetic_encoder.kicad_sch` from pin 14 (abs `(153.67, 102.87)`) up to the +3.3 V power symbol at `(140.97, 77.47)`.
   - Per MT6701 Rev 1.8 §1.2 page 4, MODE has a 200 kΩ internal pull-up; floating = high = digital mode. Per §7.1 page 10, the MODE bit selects between digital (I²C/SSI on pins 6/7/8) and incremental (ABZ/UVW). I²C and SSI **share the same pins** in digital mode and the chip auto-distinguishes by protocol activity. Per §2 page 5, MT6701QT-STD supports both. So the SSI wiring (R33-R38 → MISO/SCK/NSS) works as intended, regardless of MODE-pin state.
   - **BLOCKER removed.**

2. **DRV8316 nFAULT/nSLEEP "tied to 24V VCC, clamped by 5.1V Zener and connected to STM32 GPIOs" claim was wrong.** Prior review said "nFAULT (pin 22) and nSLEEP (pin 23) are joined and pulled up by ~100k to VCC (= +24V battery) with a BZT52B5V1S 5.1V Zener (D3, D4) clamping the node to 5.1V. The same node connects to STM32 GPIOs." Verification:
   - Pin 22 (nFAULT) and pin 23 (nSLEEP) are on **separate** nets in `motor_driver.kicad_sch`. nFAULT is via R30 330 Ω + LED4 to +3.3 V (LED-indicator pseudo-pull-up). nSLEEP is via R29 100 kΩ to +24 V VCC, clamped by D3 Zener to ~5.1 V; nSLEEP is **not** routed to the STM32 (no hierarchical label).
   - The 5.1 V clamp on nSLEEP is fine per the DRV's VIH range 1.6–5.5 V (SLVSH07 §7.5 page 10).
   - **BLOCKER changed:** new BLOCKER is that *nSLEEP has no MCU control* (DRV cannot be slept or fault-reset from firmware) and that the *nFAULT pull-up via LED+330 Ω fails the TI ">2.2 V at power-up" requirement for safe nFAULT operation* during +3.3 V rail bring-up. (Both are real issues, but distinct from the "5.1V Zener kills the GPIO" claim.)

3. **CAN common-mode choke U12 ACT1210D was claimed DNP.** Wrong: the schematic source has no `(dnp yes)` flag on U12 — it is populated. The X marks visible in the rendered schematic are part of the choke symbol's drawn coupling marks (the symbol library's geometry), not DNP rendering.
   - Note removed.

4. **DRV8316C VM abs max paraphrased as "35 V" in the previous round** — that was the recommended max (SLVSH07 §7.3 page 6). The actual abs max is **40 V** (§7.1 page 6). This affects the SMF30CA TVS clamping discussion: a clamp at 48.4 V exceeds 40 V → more critical than the prior review noted, supporting a recommendation to step down to SMF24CA.

5. **DRV8316C FOC conduction-loss formula** — the correct formula from SLVSH07 §11.3.1 Table 11-1 page 85 is **3 × IRMS² × Rds,on**, not "1.5 × IRMS²". (The prior review's assertion of 1.5 was incorrect; the corrected number is in the NIT section above.)

6. **AN4488 ferrite-bead recommendation** for VDDA was overstated as a hard requirement. AN4488 Rev 7 §3.3.2 page 14 says *"VDDA can be connected to VDD through a ferrite bead"* — *"can be"*, not *"must be"*. The 100 nF + 1 µF cap pair is the **mandatory** part. Severity downgrade from CRITICAL → NIT.

7. **ADC channel labels were claimed wrong** ("PA1 labeled ADC1_IN3 but actually ADC1_IN2", "PA2 labeled ADC1_IN4 but actually ADC1_IN3"). Verified against ST DS12288 Rev 1 Table 12 page 58: PA1 is correctly labelled ADC2_IN2 in the schematic (and PA1 = ADC12_IN2 per datasheet, so ADC2_IN2 is correct). PA2 is correctly labelled ADC1_IN3 (matches datasheet). The prior review reported the wrong labels. **Nit removed.**

8. **C1/C2 47 pF on USB-C** — prior review correctly identified these as DNP USB-C CC-compensation caps, not crystal load caps. (Confirmed.) The crystal load caps are C11/C18 = 30 pF on the HSE oscillator, also as the prior review noted. Both correct.

9. **CAN-FD termination** — prior review described the topology as "intentional middle-node, jumper-selectable" but missed that the jumper *logic* is broken in detail: with R21 alone populated, R27/R28/C30 form an asymmetric short from CAN_H to GND rather than a split termination. New BLOCKER added.

10. **QWIIC pull-ups** — prior review called this a BLOCKER and was largely correct. The detail that R18 (10 kΩ) is on SDA only (and gated by DNP J4) was correct. Adding to it: there is *no* pull-up resistor on SCL anywhere on the schematic (verified by searching all I2C_SCL label endpoints). Stays a BLOCKER.

11. **Items unchanged from prior review:** USB Type-C CC1/CC2 5.1 kΩ pulldown, NRST 100 nF cap, HSE crystal load math (Cstray ≈ 5 pF assumption), SRV05-4 ESD on D+/D-, AO3401A reverse-polarity P-FET topology. All confirmed.

---

## Items I could not verify from a primary source (flag for follow-up)

- **CA-IF1044VD-Q1 (Chipanalog) full datasheet.** LCSC's PDF host returned HTML on direct fetch (anti-leech). The Chipanalog product page wasn't reachable from my environment. I used **TI TCAN1044V-Q1 SLLSF17D** as the functional twin, but cannot guarantee Chipanalog's pin 5 has the VIO level-shifter (some Chipanalog clones have NC on pin 5 instead). Schematic owner should confirm by reading the Chipanalog datasheet locally.

- **X322512MSB4SI crystal CL = 20 pF.** Carried over from prior review; no Yangxing Tech datasheet PDF on disk. The 30 pF load-cap match works *if* CL=20 pF, but the calculation depends on this number.

- **STM32G473RBT6 datasheet (DS12288 Rev 1)** download from st.com failed twice in this environment (network timeout). I used a cached copy at `_review/datasheets/STM32G473_farnell.pdf` (DS12288 Rev 1 STM32G474xB content; functionally identical pin map for STM32G473RBT6). All pin mappings cited above came from that cached PDF.

- **AN5093 (STM32G4 hardware design getting started)** also failed to download. I used the older but applicable AN4488 (STM32F4) instead — ST's high-level recommendations on VDD/VDDA/VREF decoupling carry forward. ST has a separate ADC-specific app note (AN5346) for STM32G4 which I did not have time to read; that note typically reinforces the 100 nF + 1 µF VDDA recommendation.
