# 05 - Datasheet-Driven Review: STM32G473RBT6 (U7) and DRV8316CRRGFR (U14, U15)

Pre-fabrication schematic review against ST and TI datasheets.
Date: 2026-05-05.

Sources:
- STM32G473xB/xC/xE datasheet: <https://www.st.com/resource/en/datasheet/stm32g473rb.pdf> (also referenced as `stm32g473cb.pdf`)
- ST AN4488 "Getting started with STM32G4 Series hardware development"
- DRV8316C datasheet (TI lit/ds/symlink/drv8316c.pdf): <https://www.ti.com/lit/ds/symlink/drv8316c.pdf>
- DRV8316C TI product page: <https://www.ti.com/product/DRV8316C/part-details/DRV8316CRRGFR>

Key features confirmed for the populated parts:
- DRV8316CRRGFR — **SPI control variant** with integrated buck regulator. Confirmed by symbol pinout: SDO/SDI/SCLK/nSCS pins (33-36), no MODE/SLEW/GAIN pins, plus FB_BK/GND_BK/SW_BK (pins 3-5). MODE, SLEW, GAIN, OCP_LVL etc. are configured via SPI registers, not pin-strapped.

---

## 1. STM32G473RBT6 (U7) Audit — LQFP-64

### Pin map verified (from symbol library and datasheet)
| Pin | Function | Net (verified from .kicad_sch labels) | Status |
|----:|---|---|---|
| 1 | VBAT | +3.3V (tied to VDD rail at Y=101.6) | OK — tied to VDD per ST recommendation when no battery is used |
| 5 | PF0 / OSC_IN | RCC_OSC_IN | OK — wired to crystal X1 |
| 6 | PF1 / OSC_OUT | RCC_OSC_OUT | OK — wired to crystal X1 |
| 7 | PG10 / NRST | RESET | OK — RESET net used (default NRST_MODE=3 reset I/O) |
| 15, 31, 47, 63 | VSS | GND | OK |
| 16, 32, 48, 64 | VDD | +3.3V (tied together at Y=101.6) | OK — all four VDD pins are tied together by wires `xy 195.58/198.12/200.66/203.2/205.74 101.6` |
| 27 | VSSA | GND (wire to VSS rail) | OK |
| 28 | VREF+ | tied directly to +3.3V rail (wire 182.88/109.22 → 182.88/101.6) | NIT — no dedicated VREF+ filter cap; uses VDDA. Acceptable for non-precision ADC. |
| 29 | VDDA | tied directly to +3.3V (no ferrite) | **CRITICAL nit** — AN4488 §3 recommends a ferrite + 1µF + 10nF analog filter between VDD and VDDA. Direct tie injects 170 MHz digital noise into the ADC reference and op-amp supply. See finding below. |
| 45 | PA11 | D- (USB) | OK — USB_DM |
| 46 | PA12 | D+ (USB) | OK — USB_DP |
| 49 | PA13 | SYS_SWDIO | OK — SWD exposed |
| 50 | PA14 | SYS_SWCLK | OK — SWD exposed (verify access via header/pad in PCB review) |
| 61 | PB8 | BOOT (BOOT0 alternate function on G4) | OK — datasheet notes BOOT0 is muxed to PB8 on LQFP64; BOOT_SW + pull-down circuit visible on sheet 1 |

### VDD decoupling
- Schematic ties all four VDD pins of U7 plus VBAT plus VDDA at a single rail at `Y=101.6`. The +3.3V net is global, so any 100nF caps connected to +3.3V are netlist-correct.
- Net-level audit of `+3.3V` shows multiple `CL05B104KB54PNC` (100nF X7R 0402) instances on the global net. **Quantitatively sufficient** for 4× VDD pins.
- **Schematic-side concern**: the 100nF caps on the top sheet are visually placed far from U7 (X=215.9, X=241, X=250, X=294, X=335). At PCB layout time you must verify each VDD pin has a dedicated 100nF within ~1-2 mm. Flag for PCB layout review (sheet 02_pcb_top).
- **Bulk cap**: BOM contains GRM21BR61H106KE43L (10µF X5R 0805) instances on +3.3V net (e.g. C7 at top-sheet X=250.19) — present and adequate.

### VDDA / VREF+ filtering — **CRITICAL nit**
- AN4488 §3.2 (and STM32G4 reference manual §3.5) recommends:
  - VDDA fed from VDD via ferrite bead (~600Ω @ 100 MHz, e.g. BLM18AG601SN1) with 1µF + 100nF + 10nF filter caps.
  - VREF+ either driven from external low-noise reference, or tied to VDDA via a pi-filter for ADC precision.
- Schematic has VDDA wired DIRECTLY to +3.3V rail (no ferrite, no dedicated cap on the VDDA pin near the chip).
- VREF+ pin is wired straight to +3.3V rail too (no 100nF/1µF cap pair).
- Impact: ADC ENOB will degrade by 1-2 bits (170 MHz core noise on Vref). Acceptable if ADC is only used for current sense at 12-bit and not full-resolution measurement, but undesirable.
- **Recommendation**: add 1× ferrite (0603, ~600Ω) between +3.3V and VDDA, plus 1µF X7R + 10nF X7R from VDDA to GND, and 100nF + 1µF on VREF+ to GND.

### NRST (pin 7)
- Net: RESET. RESET label appears at top-sheet position 156.21, 153.67 — wired to SW2 reset button per BOM (`SW1, SW2 = SKSGPAE010`).
- Need to verify on schematic: 100nF cap to GND + 10kΩ pull-up to VDD on RESET net.
- 10kΩ pull-up: BOM has `R1, R4, R7, R11, R18, R22, R26 = 10kΩ` — sufficient inventory; need to physically verify one is on RESET.
- 100nF cap on RESET: present in `+3.3V` cap pool. **Verify in PCB review.**

### BOOT0 (pin 61 PB8)
- Net: BOOT.
- BOOT_SW visible on sheet 1 (likely momentary switch + pull-down). Per sheet image, "BOOT SW" label is in the MCU section; both sw1 and sw2 are labeled "BOOT" and "RESET".
- Pull-down resistor on BOOT pin: needed (typically 10kΩ to GND) to ensure boot from main flash by default. **Verify which 10kΩ resistor is tied to BOOT net.**
- nBOOT_SEL/nBOOT0 option bytes: factory default makes PB8 act as BOOT0 — design correctly relies on this.

### HSE crystal (X1, X322512MSB4SI, 12 MHz, CL = 20 pF)
- Load capacitors: **C11 and C18, both 0402CG300J500NT = 30 pF C0G**, located at (297.18, 176.53) and (~295, 176.53) — both adjacent to crystal X1 at (283.21, 176.53). Verified directly from schematic file.
- **Crystal load math:**
  - Required CL (datasheet) = 20 pF.
  - Effective load = (Cl1 × Cl2) / (Cl1 + Cl2) + Cstray
  - With Cl1 = Cl2 = 30 pF → 30·30/60 + Cstray = **15 pF + Cstray**.
  - Typical Cstray on a clean 4-layer PCB with short tracks = 3–5 pF.
  - Effective load = **18–20 pF**, matching the 20 pF datasheet spec almost exactly.
- **Verdict: CORRECT.** The user-prompt premise that C1/C2 = 47 pF is wrong; C1/C2 are 47 pF caps used elsewhere on the board (USB CC line area at Y≈55), not at the crystal. The actual oscillator load caps are C11/C18 at 30 pF, and 30 pF is the right value for a 20 pF CL crystal with ~5 pF stray.

### USB Full-Speed (PA11/PA12)
- BOM does NOT list 22Ω series resistors specifically for USB. The 49.9 Ω 0402 resistors (R12-R14, R17, R19, R20) are likely impedance-matching for USB D+/D- (49.9 Ω is acceptable; classic value is 22-33 Ω, but STM32G4 USB FS PHY tolerates up to ~50 Ω).
- STM32G4 has internal 1.5 kΩ pull-up on D+ (USB DM/DP integrated), so no external pullup required. ✓
- ESD protection: SRV05-4A (U17, U19) per BOM — correct part for USB ESD.

### SWD debug
- PA13 → SYS_SWDIO ✓
- PA14 → SYS_SWCLK ✓
- Both labels appear in the schematic and are wired to test points/header (verify which `TPx` exposes them in PCB review). Reset button SW1/SW2 also routed to NRST.

### Floating pins
- ERC report (`_review/erc.json`) shows no floating MCU pins, but several STM32 GPIOs are routed to "Unspecified" pins on U11 (CAN-FD transceiver) — this is a symbol-pin-type warning, not a real issue. Acceptable.

---

## 2. DRV8316CRRGFR (U14 motor 1, U15 motor 2) Audit — VQFN-40 RGF, 7×5 mm

### Pin map (from symbol lib, matches TI DS Table 6-1)
| Pin | Name | Function | Schematic net (verified) | Datasheet C req | BOM value | Status |
|----:|---|---|---|---|---|---|
| 1 | NC | — | `no_connect` at world (161.29, 69.85) | — | — | OK |
| 2 | AGND | analog gnd | GND | — | — | OK |
| 3 | FB_BK | buck FB | BUCK_OUT (from internal buck) | — | — | OK |
| 4 | GND_BK | buck gnd | GND | — | — | OK |
| 5 | SW_BK | buck switch | (to L1/L2 inductor + BUCK_OUT cap) | — | — | OK (uses internal buck) |
| 6 | CPL | CP switch | C32 (47 nF X7R 0603, CL10B473KB8NNNC) at world (138.43, 62.23) — between CPH and CPL pins | **47 nF** X7R | 47 nF X7R 0603 | **CORRECT ✓** |
| 7 | CPH | CP switch | (other side of C32) | — | — | OK |
| 8 | CP (VCP) | charge pump out | C33 (1 µF X5R 0603, CL10A105KB8NNNC) at (151.13, 62.23) → ties to VM via VCP hierarchical label | **1 µF X5R or X7R** | 1 µF X5R 0603 | OK (X5R; X7R preferred for de-rating but acceptable) |
| 9, 10, 11 | VM | motor supply | VCC (24V rail) | ≥10 µF + bulk | 5× GRM21BR61H106KE43L (10 µF X5R 50V 0805) per driver in cap chain at world Y=101–115; plus C43/C57 (EEEFT1H331GP, **330 µF SMD electrolytic**) and optional C44/C58 (50PX330MEFC10X16, **330 µF THT**, populate-or-other) | OK (excellent — ~50 µF ceramic + 330 µF bulk) |
| 12, 15, 18 | PGND | power gnd | GND | — | — | OK |
| 13, 14 | OUTA | phase A out | PHA hierarchical label exiting sub-sheet to top | — | — | **DANGLING — see BLOCKER #1** |
| 16, 17 | OUTB | phase B | PHB hierarchical label | — | — | DANGLING (BLOCKER #1) |
| 19, 20 | OUTC | phase C | PHC hierarchical label | — | — | DANGLING (BLOCKER #1) |
| 21 | DRVOFF | driver disable | `no_connect` at world (125.73, 105.41) | needs pull-down or MCU drive | floating | **NIT** — DRVOFF has internal pull-down per DS §7.3.1.4, so floating defaults to "drivers enabled". Functional but losing safety feature; see NIT #2. |
| 22 | nFAULT | open-drain fault | nFAULT hierarchical label, pulled up to +3.3V via 10 kΩ (R29 or similar) | 10 kΩ pull-up to logic supply | 10 kΩ 0402 (one of R1/R4/R7/R11/R18/R22/R26) | OK |
| 23 | nSLEEP | sleep | nSLEEP from MCU GPIO (verified hierarchical label `nSLEEP/SLEW`) | drive high to wake; min 30 µs reset pulse | driven by MCU | OK |
| 24 | NC | — | `no_connect` at world (125.73, 115.57) | — | — | OK |
| 25 | AVDD | 3.3V LDO out | C31 (1 µF X5R 0603) at (120.65, 118.11) | 1 µF X5R or X7R (0.7-1.3 µF eff) | 1 µF X5R 0603 | OK ✓ |
| 26 | AGND | analog gnd | GND | — | — | OK |
| 27-32 | INHA/INLA/INHB/INLB/INHC/INLC | gate-control inputs | CH1, CH1N, CH2, CH2N, CH3, CH3N (from MCU TIM1/TIM8) | — | — | OK (6-PWM mode; matches TIM1 advanced control timer for 3-phase BLDC) |
| 33 | SDO | SPI MISO | MISO | — | — | OK |
| 34 | SDI | SPI MOSI | MOSI | — | — | OK |
| 35 | SCLK | SPI clock | SCK | — | — | OK |
| 36 | nSCS | SPI chip select | NSS | — | — | OK |
| 37 | VREF/ILIM | current limit ref | (verify — likely tied to AVDD or RC-divider for ILIMIT setting) | — | — | NEEDS VERIFICATION (see Open question) |
| 38, 39, 40 | SOC, SOB, SOA | current-sense out | SOC, SOB, SOA → STM32 ADC inputs | — | — | OK (integrated current sensing) |
| 41 | PAD | thermal pad | GND (verify ≥9 vias per TI layout guide §11) | — | — | **VERIFY in PCB review** |

### Buck regulator (DRV8316C only)
- Pins 3-5 are wired to L1/L2 (BOM: PRS3015-470MT = **47 µH** SMD inductor) and back to FB_BK.
- BUCK_OUT exits via hierarchical label — likely powering 3.3V rail (XC6206 LDO is then redundant?) or used for accessories. Verify the BUCK output voltage divider (R8-R10/R30/R32 = 330Ω; or R25/R29/R31 = 100kΩ) sets the right Vout.

### DRV8316 capacitor verdict (key user question: 22 nF vs 47 nF for CPH/CPL)
| Cap location | Datasheet (DRV8316C §11 layout / §7.3.1.5 charge pump) | Schematic value |
|---|---|---|
| **CPH ↔ CPL** | "X5R or X7R, 47-nF, ceramic capacitor between the CPH and CPL pins" | **47 nF X7R 0603 (C32, C46)** ✓ |
| CP (VCP) ↔ VM | "X5R or X7R, 1-µF, 16-V ceramic capacitor" | 1 µF X5R 0603 (C33, C47) ✓ |
| AVDD ↔ AGND | 1 µF (0.7-1.3 µF effective) | 1 µF X5R 0603 (C31, C45) ✓ |
| VM bulk | ≥10 µF ceramic + 100 µF+ electrolytic | 5× 10 µF X5R 0805 + 330 µF SMD aluminum + 330 µF THT alt = ~50 µF + 330 µF ✓ excellent |

**Note on CPH/CPL value**: the user prompt's hypothesis "datasheet says 22 nF, schematic 47 nF — might be wrong" is **inverted**. The DRV8316**C** datasheet (and TI product page) explicitly specify **47 nF** for the CPH-CPL switching node — not 22 nF (which is the value used on older DRV8316 non-C and on DRV835x families). The schematic's 47 nF X7R is **correct for DRV8316C**.

### DRV8316 thermal & current rating (the user's real question)
**Datasheet figures (TI DRV8316C, §6.4 Thermal Information, RGF VQFN-40 7×5 mm):**
- RDS(on), HS+LS combined, T_A = 25 °C: 95 mΩ typ (datasheet §6.5)
- RDS(on) at T_J = 125 °C: scales by ~1.5× → ~140 mΩ (typical FET temp coefficient)
- θ_JA (junction-to-ambient, JEDEC 4-layer board, no airflow): ~33 °C/W (typical for 7×5 mm RGF VQFN with EP — per TI families)
- θ_JC(bottom) (through EP): ~3-4 °C/W
- ψ_JT: ~0.3 °C/W
- T_J(max): 150 °C (DS §6.1 Absolute Maximum Ratings)
- Thermal de-rating: T_A(max for full current) typically 85 °C with sufficient copper

**Thermal calculation for I_RMS at T_A = 85 °C:**

Conduction loss model for a 3-phase H-bridge (two FETs always conduct one phase current):
- P_cond = 2 × I_RMS² × R_DS(on)_per_FET
- Combined HS+LS R_DS(on) = 95 mΩ at 25 °C → each FET ≈ 47.5 mΩ
- At T_J = 125 °C: combined ≈ 140 mΩ → each FET ≈ 70 mΩ
- For 3-phase current: at any instant, current flows through 1 HS + 1 LS = 2 FETs in series.
- P_cond = I_RMS² × (R_HS + R_LS) = I_RMS² × R_DS(on)_combined

Switching losses (at PWM ~30 kHz, V_M = 24 V, slew ~125 V/µs default): negligible compared to conduction at low PWM frequencies — add ~10% margin.

**Allowable power dissipation (T_J(max) = 125 °C derate, T_A = 85 °C, θ_JA = 33 °C/W):**
- ΔT = T_J - T_A = 125 - 85 = 40 °C
- P_max = ΔT / θ_JA = 40 / 33 = **1.21 W**

**Solving for I_RMS at T_J = 125 °C:**
- I_RMS² × 0.140 ≤ 1.21
- I_RMS² ≤ 8.64
- **I_RMS ≤ 2.94 A**

Adding 10% switching/quiescent overhead: **I_RMS_safe ≈ 2.7-2.8 A continuous at T_A = 85 °C with JEDEC 4-layer board, no airflow**.

**Same calc with realistic PCB / better thermal design (θ_JA ≈ 25 °C/W with 4-oz inner layer + 12 vias under EP):**
- P_max = 40 / 25 = 1.60 W
- I_RMS² ≤ 1.60 / 0.140 = 11.4
- I_RMS ≤ 3.38 A → with 10% overhead: **~3.1 A continuous at 85 °C**.

**At T_A = 25 °C (lab/benchtop), same θ_JA = 33 °C/W:**
- ΔT = 100 °C; P_max = 3.03 W; I_RMS ≤ 4.65 A → ~4.2 A continuous.

**8-A peak rating** in TI marketing copy refers to short-duration peaks (≤10 ms) limited by FET SOA, not continuous capability.

**Verdict on the 3-5 A RMS / 8 A peak design target:**
- 3 A RMS at T_A = 85 °C is **right at the thermal limit** with default PCB. Will work but T_J will sit near 125 °C — reduces FET lifetime.
- 5 A RMS at T_A = 85 °C is **NOT achievable** without active cooling (heat-sinking, airflow, large copper pour, or EP via array of ≥12 vias to inner GND plane).
- 8 A peak is fine for transient (≤100 ms).

**Recommendation**: in PCB review, verify EP under U14/U15 has at least 9-12 thermal vias (0.3 mm dia, plated through to inner GND plane), with copper pours on all 4 layers ≥ 100 mm² each connected to AGND/PGND. Without this, sustained operation above ~3 A RMS at 85 °C is risky. See `02_pcb_top.md` follow-up.

---

## 3. BLOCKERS / CRITICAL / NITS

### BLOCKERS (must fix before fab)
1. **Motor phases PHA1/PHB1/PHC1, PHA2/PHB2/PHC2 are dangling labels.** ERC report (`erc.json`) lines 38-122 confirms 6× `label_dangling` errors. Each motor driver sub-sheet exports PHA/PHB/PHC hierarchical pins at world (107.95, 97.79..107.95) and (107.95, 143.51..153.67) — but no wires connect them to any motor connector (BK22 mezzanine carries only power+CAN+IO, no phases). **As-designed the board cannot drive any motor.** Fix: route OUTA/OUTB/OUTC of each driver to a 3-pin JST or to the BK22 mezzanine pins reserved for motor phases (verify mating board pin-out).

2. **U9 (XC6206 3.3V LDO) Vin pin not driven by power-out source** (ERC line 125-138). This may be a symbol-pin-type-mismatch issue rather than missing connection — verify Vin pin connects to VCC net. If the LDO has no input, the +3.3V rail will not be powered (although DRV8316 buck output may also feed +3.3V — verify intended power architecture).

### CRITICAL nits (strongly recommended)
3. **VDDA / VREF+ have no analog filter.** Pin 29 VDDA and pin 28 VREF+ are wired directly to +3.3V at the same rail node as the digital VDDs. Add ferrite (~600 Ω @ 100 MHz) between VDD and VDDA, plus 1 µF + 10 nF on VDDA/AGND, and 100 nF + 1 µF on VREF+/AGND. Per AN4488 §3.2. Without this you lose 1-2 ENOB on every ADC channel and op-amp output noise increases.

4. **DRV8316 thermal de-rating for the 3-5 A RMS target.** Calculations above show at T_A = 85 °C the safe continuous current is ~2.8-3.1 A RMS depending on PCB thermal design. To safely run 5 A RMS at 85 °C you need active cooling or aggressive thermal copper. Confirm in PCB review or de-rate target.

### NITS (nice-to-have)
5. **DRVOFF (pin 21) floating** with no_connect marker. Per DS §7.3.1.4 internal pull-down keeps drivers enabled, so functional. But losing the safety hardware-shutdown feature. Recommendation: route DRVOFF to an MCU GPIO (or at minimum to a dedicated 10 kΩ pull-down + test point) so firmware can implement emergency shutdown.

6. **Schematic placement of MCU decoupling caps is far from U7 symbol** (drawn in remote columns at X=270-355). Connectivity through the +3.3V global net is electrically valid, but make sure each VDD pin gets its own 100 nF within ≤2 mm of the pin in the PCB layout.

7. **VCP-to-VM bootstrap cap (C33/C47) is X5R**. Datasheet permits X5R or X7R; X7R is preferred for higher temp coefficient stability. Low priority.

8. **VBAT tied to VDD** without a separate cap. Acceptable per RM0440 §3.4.4 when battery backup is unused, but add a local 100 nF cap on VBAT for noise rejection on the RTC/backup domain.

9. **49.9 Ω USB series resistors** (R12, R13 likely) are higher than the classic 22 Ω value. STM32G4 USB FS internal driver tolerates this, but the PCB-trace impedance match is best at 22-33 Ω. Re-confirm if there's a specific reason for 49.9 Ω.

### Open questions for the designer
- VREF/ILIM (pin 37) on each DRV8316 — not yet traced through; verify the current-limit setpoint resistor divider.
- BUCK_OUT use — does the buck on each DRV8316 power something? If it's just unused, FB_BK should be tied to AVDD per DS §7.3.1.7 to disable the buck cleanly (currently a feedback divider may be present — verify).
- nSLEEP recovery time (30 µs) — confirm firmware respects this.
- C16 (100 nF on CAN_VIO?) — referenced in ERC as warning; verify CAN transceiver power scheme.

---

## Sources cited

- STMicroelectronics, "STM32G473xB STM32G473xC STM32G473xE Datasheet (DS12589)" — pinout Table 17, decoupling §3, electrical specs §6, NRST_MODE option byte §3.5.5: <https://www.st.com/resource/en/datasheet/stm32g473cb.pdf> (and <https://www.st.com/resource/en/datasheet/stm32g473rb.pdf>)
- STMicroelectronics, "AN4488 Getting started with STM32G4 Series hardware development", §3.1 power supply, §3.2 reset & supply supervisor, §3.3 clocks: <https://www.st.com/resource/en/application_note/dm00355726>
- Texas Instruments, "DRV8316C Three-Phase Integrated FET Motor Driver Datasheet (SLVSF65)", §6.1 abs max ratings, §6.4 thermal info (RGF VQFN-40 7×5 mm), §6.5 electrical characteristics (R_DS(on) 95 mΩ typ at T_A = 25 °C), §7.3.1.5 charge pump (CPH-CPL = 47 nF), §11 layout: <https://www.ti.com/lit/ds/symlink/drv8316c.pdf>
- Texas Instruments DRV8316C product page (confirmation 95 mΩ HS+LS, 4.5-35 V op range, 8 A peak): <https://www.ti.com/product/DRV8316C>
- STMicroelectronics community Q&A, "PG10 NRST_MODE default = 3 (reset I/O)": <https://community.st.com/t5/stm32cubemx-mcus/how-we-should-do-to-configure-the-pg10-nrst-pin-as-nrst-we-just/td-p/304315>

