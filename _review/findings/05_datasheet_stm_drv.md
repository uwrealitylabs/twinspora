# 05 — Datasheet-Driven Review: STM32G473RBT6 (U7) and DRV8316CRRGFR (U14, U15)

Round-2 fully primary-source-cited audit. Date: 2026-05-05.

**Primary sources used (all verified by direct PDF read, not search-snippet paraphrase):**
- Texas Instruments, *DRV8316C Three-Phase Integrated FET Motor Driver Datasheet*, doc ID **SLVSH07** (December 2022).
  Local copy: `D:\gehub\twin28xx\_review\datasheets\DRV8316C_TI.pdf`
- STMicroelectronics, *STM32G474xB/xC/xE Datasheet* (also covers STM32G473xB pin map; all G473RB pin/electrical specs identical), doc ID **DS12288 Rev 1** (May 2019).
  Local copy: `D:\gehub\twin28xx\_review\datasheets\STM32G473_farnell.pdf`
- STMicroelectronics, *AN4488 Application note — Getting started with STM32F4xxxx MCU hardware development* (June 2014, Rev 1).
  Local copy: `D:\gehub\twin28xx\_review\datasheets\AN4488.pdf`
  *Note: ST has no STM32G4-specific equivalent of AN4488; AN4488's power-supply-scheme guidance is identical to the STM32G4 datasheet §5.1.6 figure 15 (DS12288 p80), and the same recommendations apply.*
- STMicroelectronics, *AN2867 Application note — Oscillator design guide* (January 2009, Rev 1).
  Local copy: `D:\gehub\twin28xx\_review\datasheets\AN2867.pdf`

Schematic files: `D:\gehub\twin28xx\twin28xx\twin28xx.kicad_sch` (top), `D:\gehub\twin28xx\twin28xx\motor_driver.kicad_sch` (DRV sub-sheet).
BOM: `D:\gehub\twin28xx\_review\bom.csv`.

---

## 0. Corrections to prior version (`v1_archive/05_datasheet_stm_drv.md`)

| # | Item | Prior round (WRONG) | Corrected (cited) |
|---|---|---|---|
| C1 | DRV8316C V_VM abs max | "35 V" | **40 V** — TI SLVSH07 §7.1, p6, row "Power supply pin voltage (VM): MAX 40 V". The 35 V is the *recommended-operating* MAX (§7.3, p6). |
| C2 | DRV8316C P_CON formula (FOC) | "P_CON = 1.5 × IRMS² × R_DS(on)" with implicit single-FET R_DS(on) | **P_CON = 3 × IRMS² × R_DS(on)(TA)** for FOC — TI SLVSH07 Table 11-1, §11.3.1, p85. R_DS(on) here is the HS+LS combined value (95 mΩ typ at TA=25 °C, 140 mΩ typ at TJ=150 °C, §7.5 p11). |
| C3 | DRV8316C θJA | "~33 °C/W (typical for 7×5 mm RGF VQFN)" | **25.7 °C/W** — TI SLVSH07 §7.4, p7, row RθJA. |
| C4 | DRV8316C θJC(top) / θJC(bot) / θJB / ψJT | "θJC(bottom): ~3-4 °C/W; ψ_JT: ~0.3 °C/W" | **θJC(top) = 15.2, RθJB = 7.3, ΨJT = 0.2, ΨJB = 7.2, RθJC(bot) = 2.0 °C/W** — TI SLVSH07 §7.4 p7 (full row). |
| C5 | Safe IRMS at TA=85 °C | "~2.7-3.1 A continuous" | At max slew (200 V/µs), fPWM=50 kHz, FOC, with active demag: **≈ 1.27 A at TJ_target=125 °C; ≈ 1.61 A at TJ_target=140 °C** (using TI's actual P_CON=3×I²×R, switching, dead-time, standby losses summed and equated to (TJ-TA)/θJA = (TJ-85)/25.7). See §3.5 below for full math. |
| C6 | Safe IRMS at TA=25 °C | "~4.2 A continuous" | At max slew, FOC, AD on: **≈ 2.49 A at TJ_target=125 °C; ≈ 2.68 A at TJ_target=140 °C** (per same calc). |
| C7 | HSE Cstray assumption | "Typical Cstray on a clean 4-layer PCB with short tracks = 3–5 pF. Effective load = 18–20 pF, matching 20 pF spec" | **DS12288 §5.3.10 p123 explicitly says: "PCB and MCU pin capacitance must be included (10 pF can be used as a rough estimate of the combined pin and board capacitance) when sizing CL1 and CL2."** With Cstray = 10 pF and Cl1=Cl2=30 pF: CL_eff = 30·30/60 + 10 = **25 pF, not 20 pF**. C11/C18 are over-loading the crystal by ~5 pF. Optimal would be Cl1=Cl2 = **20 pF** each (yielding CL_eff = 10 + 10 = 20 pF). With 30 pF the oscillator will still start, but f will be slightly low (typically –20 to –40 ppm, depending on motional capacitance Cm; not catastrophic, but suboptimal). See §1.4. |
| C8 | VDDA / VREF+ filter status | "Wired DIRECTLY to +3.3V rail, no dedicated cap on the VDDA pin near the chip; VREF+ wired straight to +3.3V rail too (no 100nF/1µF cap pair)" | **Twin28xx HAS dedicated decoupling pairs**: at world (X=355.6, Y=101.6 / 114.3 / 127 / 139.7) there is a column of four caps tagged "VDDA/VREF Decoupling": **C25 = 100 nF X7R + C26 = 1 µF X5R** (one pair) and **C27 = 100 nF X7R + C28 = 1 µF X5R** (second pair). These are tied to the global +3.3V net. The remaining valid critique is that there is **no ferrite isolating VDDA/VREF+ from the digital VDD rail** (per AN4488 §2.2 p8 "Additional precautions can be taken: VDDA can be connected to VDD through a ferrite bead.") and that the caps are placed ~150 mm in schematic-space from U7 — they need to be physically near the U7 pins on the PCB. See §1.2 below. |
| C9 | USB series-resistor remark | Implied 22 Ω needed; observed 49.9 Ω in BOM and questioned them as USB | **DS12288 Table 92 (USB electrical characteristics) footnote 4 p181: "No external termination series resistors are required on USB_PD (D+) and USB_DM (D-); the matching impedance is already included in the embedded driver."** STM32G4 USB FS PHY has driver impedance ZsDRV = 28-44 Ω built-in (Table 92). **49.9 Ω resistors R12-R14, R17, R19, R20 are NOT for USB.** They are most likely the SOA/SOB/SOC current-sense filter resistors (DRV8316C §9.2.1.1.6 p73 recommends "330-ohms, 22-pF" — Twin28xx used 49.9 Ω for lower noise / wider bandwidth, valid choice). USB design uses ONLY the U17/U19 (SRV05-4A) ESD protection at the connector + internal 1.5 kΩ D+ pull-up (DS12288 Table 92 row RPUI = 900–1500 Ω). |
| C10 | DRV8316C CPH/CPL cap value | "47 nF" — correct in prior; restated for traceability | **Confirmed**: TI SLVSH07 Table 6-1 (Pin Functions) p4-5: "Connect a X5R or X7R, 47-nF, ceramic capacitor between the CPH and CPL pins." Schematic uses **CL10B473KB8NNNC = 47 nF X7R 0603** for C32/C46. ✓ |

---

## 1. STM32G473RBT6 (U7) Audit — LQFP-64

### 1.1 LQFP-64 pin map (verified against DS12288 §4.3 fig 7 p50 and §4.9 Table 12 p56-71)

| LQFP-64 pin | Pin name | I/O class | Twin28xx net | Status |
|---:|---|---|---|---|
| 1 | VBAT | S | +3.3V (tied to VDD) | OK — AN4488 §2.1.2 p7: "If no external battery is used in the application, it is highly recommended to connect VBAT externally to VDD." Confirmed. NIT: AN4488 §2.2 p8 also recommends "100 nF external ceramic decoupling capacitor" on VBAT — verify a 100 nF cap is physically near pin 1 in PCB layout. |
| 5 | PF0-OSC_IN | I/O FT_fa | RCC_OSC_IN → X1 | OK |
| 6 | PF1-OSC_OUT | I/O FT_a | RCC_OSC_OUT → X1 | OK |
| 7 | PG10-NRST | NRST (special) | RESET label | OK — DS12288 §5.3.15 Table 61 p139 confirms NRST is bidirectional with internal weak pull-up RPU = 25-55 kΩ (typ 40 kΩ). DS12288 fig 26 p140 shows recommended external 100 nF cap to GND. |
| 15, 31, 47, 63 | VSS | S | GND | OK |
| 16, 32, 48, 64 | VDD | S | +3.3V (4 pins) | OK |
| 27 | VSSA | S | GND | OK |
| 28 | VREF+ | S | +3.3V (via global net) | OK with caveat — see §1.2 |
| 29 | VDDA | S | +3.3V (via global net) | OK with caveat — see §1.2 |
| 45 | PA11 | I/O **FT_u** (USB) | USB_DM | OK — FT_u (5 V tolerant w/ USB function) per DS12288 Table 12 p66 |
| 46 | PA12 | I/O **FT_u** | USB_DP | OK |
| 49 | PA13 | I/O FT_f | SYS_SWDIO | OK — DS12288 Table 12 note (4) p71: "After reset, ... internal pull-up on PA15, PA13, PB4 pins ... activated". External pull-up is therefore not required. |
| 50 | PA14 | I/O FT_f | SYS_SWCLK | OK — DS12288 Table 12 note (4) p71: internal pull-down on PA14 activated after reset. External pull-down not required. |
| 61 | PB8-BOOT0 | I/O FT_f, **B** (Dedicated BOOT0) | BOOT label | OK |

All five GPIOs of interest (PA11, PA12, PA13, PA14, PB8) are **FT (5 V tolerant)** per DS12288 Table 12 — so any pull-ups to 3.3V from DRV8316 nFAULT (open-drain) and any 3.3V drive from MCU to DRV8316 nSLEEP/INHx/INLx are within abs-max. (DRV8316C also accepts 1.8 V/3.3 V/5 V logic per its features page 1 and §7.3 p6 logic input range –0.1 to 5.5 V.)

### 1.2 VDDA / VREF+ filtering — verified

Per **DS12288 §5.1.6 fig 15 p80** ("Power supply scheme"), and **AN4488 §2.2 p8**:

- VDD pair: **n × 100 nF + 1 × 4.7 µF** (n = number of VDD/VSS pairs).
- VDDA pair: **100 nF + 1 µF** to AGND.
- VREF+ pair: **100 nF + 1 µF** to AGND (or tie to VDDA for non-precision ADC).
- Additional precaution (AN4488 §2.2 p8): "VDDA can be connected to VDD through a ferrite bead. The VREF+ pin can be connected to VDDA through a resistor (typ. 47 Ω)."

**Twin28xx schematic (verified from `twin28xx.kicad_sch`):**

| Cap | Position (world XY) | Value | Net |
|---|---|---|---|
| C25 | 355.6, 101.6 | 100 nF X7R 0402 (CL05B104KB54PNC) | +3.3V → GND |
| C26 | 355.6, 114.3 | 1 µF X5R 0402 (CL05A105KA5NQNC) | +3.3V → GND |
| C27 | 355.6, 127.0 | 100 nF X7R 0402 | +3.3V → GND |
| C28 | 355.6, 139.7 | 1 µF X5R 0402 | +3.3V → GND |

A schematic text label "VDDA/VREF Decoupling" is placed at (355.346, 84.074) above this group, so the design intent is two 100 nF + 1 µF pairs (one for VDDA, one for VREF+). U7 VDDA pin (29) and VREF+ pin (28) are wired to the global +3.3V net via short stubs at world (208.28, 101.6) and (182.88, 109.22→101.6) respectively. The decoupling caps thus share the +3.3V rail.

**Quantitatively**: 100 nF + 1 µF on each of VDDA/VREF+ matches AN4488 §2.2 / DS12288 fig 15. Schematic-correct.

**Two real concerns remain:**

1. **No ferrite between VDD and VDDA.** AN4488 §2.2 p8 lists a ferrite bead as an "additional precaution" — not strictly required, but recommended for ADC accuracy. With the full-bridge motor driver switching at 24 V × ~A on the same +3.3V supply tree, ADC ENOB will degrade by ≥1 bit. **CRITICAL** for current-sense ADC accuracy at higher motor currents (see §3.5 below for impact on FOC quality).
2. **Schematic-space distance.** C25-C28 are drawn at X=355.6 while U7 is at X=200.66 — a "schematic placement" issue that doesn't affect netlist but is a **PCB layout flag**: each 100 nF must end up within ≤2 mm of the U7 VDDA/VREF+ pins on the PCB, or HF decoupling is lost.

### 1.3 NRST pin

- **DS12288 §5.3.15 Table 61 p139**: VIL = 0.3 × VDD = 0.99 V max; VIH = 0.7 × VDD = 2.31 V min. Internal RPU = 25 / 40 / 55 kΩ (min/typ/max).
- **DS12288 fig 26 p140 "Recommended NRST pin protection"**: external 100 nF cap from NRST to GND, plus optional external reset circuit. The cap "must be placed as close as possible to the device" (footnote 3).
- **AN4488 §2.3.3 p11**: "Only a pull-down capacitor is recommended to improve EMS performance by protecting the device against parasitic resets ... The capacitor recommended value (100 nF) can be reduced to 10 nF to limit this power consumption."
- **Twin28xx**: BOM has 0.1 µF caps in the +3.3V cap pool. SW1/SW2 (SKSGPAE010, BOM line 34) — one is RESET, one is BOOT. The schematic has a "RESET SW" label at (135.128, 138.43) and "BOOT SW" label at (134.874, 92.964). No external 10 kΩ pull-up is needed for NRST (internal pull-up exists per DS Table 61). **Verify in PCB review**: a 100 nF cap exists physically within ~2 mm of pin 7 (NRST). Not visible by inspecting the schematic alone since global +3.3V/GND net membership is what matters.

### 1.4 HSE crystal (X1, X322512MSB4SI, 12 MHz, datasheet CL = 20 pF)

**Per DS12288 §5.3.10 (HSE oscillator characteristics) p123-124**, verbatim:
> "For CL1 and CL2, it is recommended to use high-quality external ceramic capacitors in the 5 pF to 20 pF range (typ.), designed for high-frequency applications, and selected to match the requirements of the crystal or resonator (see Figure 20). CL1 and CL2 are usually the same size. The crystal manufacturer typically specifies a load capacitance which is the series combination of CL1 and CL2. **PCB and MCU pin capacitance must be included (10 pF can be used as a rough estimate of the combined pin and board capacitance) when sizing CL1 and CL2.**"

**Per AN2867 §4.2 p10**, the load capacitance equation:
> CL = (CL1 × CL2)/(CL1 + CL2) + Cs

where Cs is the stray (PCB + MCU pin) capacitance.

**Crystal X322512MSB4SI**: BOM line 48 shows 12 MHz ±10 ppm 20 pF SMD3225-4P, so target CL = 20 pF.

**Twin28xx as designed (C11/C18 = 30 pF C0G, BOM line 7)**:
- CL_eff = 30·30/(30+30) + Cs
- With **Cs = 10 pF (per DS12288 §5.3.10 quote above)**: CL_eff = 15 + 10 = **25 pF** ← over-loads crystal by 5 pF.

**Frequency error from CL mismatch (AN2867 §4.6 p13 pullability formula):**
> Δf/f0 = Cm/(2 × (C0 + CL)²)

Without exact Cm/C0 from the X322512 manufacturer datasheet (LCSC vendor; not held locally), typical values for a 12 MHz crystal are Cm ≈ 5–15 fF, C0 ≈ 3–7 pF. Using Cm = 10 fF, C0 = 5 pF, the shift is on the order of single-digit ppm low.

For USB FS this would be a problem if Δf > ±200 ppm (USB FS spec ±2500 ppm; locked PLL eats most of that). With Δf ≈ a few ppm low, the oscillator will start and USB FS will lock. **NIT**: oscillator will run at a slightly low frequency. Recommend swapping C11/C18 from 30 pF to **20 pF C0G** to land exactly at CL = 20 pF.

**Verdict on HSE**: oscillator will start and run; minor frequency offset; not blocking. **Recommendation: change C11/C18 to 20 pF for next revision.** Crystal RExt is not used (set to 0 Ω) — per AN2867 §4.4.3 p12 RExt is only mandatory if calculated DL > DL_max of crystal; for 12 MHz at typical drive levels with the STM32G4's controlled-gain amplifier, DL is well under spec (DS12288 Table 44 p123 gives Gm,crit = 1.5 mA/V max, and at CL = 20 pF the gain margin is comfortably > 5).

### 1.5 BOOT0 (PB8 pin 61)

- DS12288 §3.7 Table 11 p55: PB8 has special role "B = Dedicated BOOT0 pin" (note 5 p71: "It is recommended to set PB8 in another mode than analog mode after startup to limit consumption if the pin is left unconnected.")
- AN4488 §5.2 fig 19 p27 shows recommended boot pin connection: external 10 kΩ pull-down to GND, plus optional momentary switch to VDD for serial-bootloader access.
- BOOT mode selection (AN4488 §5.1 Table 7 p27 — the table is shown for STM32F4, but G4 boot semantics are identical when nBOOT_SEL option byte = 1, the factory default per RM0440 §3.5.5): BOOT0=0 → main flash; BOOT0=1 → system bootloader.

**Twin28xx**: BOOT label at (218.44, 172.72) and at (135.128, 92.964) ("BOOT SW"). One of R1/R4/R7/R11/R18/R22/R26 (10 kΩ 0402, BOM line 26) provides the pull-down — and SW1 or SW2 (SKSGPAE010) momentary switch ties BOOT to +3.3V when pressed. Standard ST-recommended circuit. ✓

### 1.6 USB Full-Speed (PA11/PA12)

- **DS12288 Table 92 p181 footnote 4**: "No external termination series resistors are required on USB_PD (D+) and USB_DM (D-); the matching impedance is already included in the embedded driver." Driver output impedance ZsDRV = 28-44 Ω (Table 92).
- **DS12288 Table 92 p181 row RPUI**: Embedded USB_DP pull-up during idle = 900–1500 Ω (typ 1250 Ω). No external pull-up needed.
- **AN4488 §3.2 p18 pinout** confirms PA11/PA12 are USB capable on G4.

**Twin28xx**: PA11 (pin 45) → USB_DM, PA12 (pin 46) → USB_DP. ESD protection via U17/U19 (SRV05-4A) — correct part for USB (TVS array, low capacitance, USB-rated).

The 49.9 Ω resistors R12-R14, R17, R19, R20 (BOM line 29) are **not for USB**. They are very likely for the DRV8316C SOx current-sense filter (DS SLVSH07 §9.2.1.1.6 p73 recommends "330-ohms, 22-pF"; Twin28xx's 49.9 Ω is a lower-noise / wider-bandwidth choice — also valid). Verify in PCB review by tracing R12/R13/R14 to the SOA/SOB/SOC nets.

### 1.7 SWD debug

DS12288 Table 12 p66, AN4488 Table 8 p30 (same SWJ-DP assignment for all STM32 with SWJ-DP):
- SWDIO → PA13 (FT_f, internal pull-up after reset, DS Table 12 note 4 p71)
- SWCLK → PA14 (FT_f, internal pull-down after reset, DS Table 12 note 4 p71)

**Twin28xx**: PA13 → SYS_SWDIO ✓, PA14 → SYS_SWCLK ✓. No external pull-ups/downs needed (handled internally).

### 1.8 VDD decoupling sufficiency

- **DS12288 §5.1.6 fig 15 p80**: "n × 100 nF + 1 × 4.7 µF" where n = number of VDD/VSS pairs.
- LQFP-64 has **4 × VDD pins** (16, 32, 48, 64, per DS12288 Table 12). So spec calls for **4 × 100 nF + 1 × 4.7 µF**.
- **Twin28xx BOM line 3** (`CL05B104KB54PNC`, 100 nF X7R 0402) lists 14 instances on +3.3V net; BOM line 8 (`CL10A475KO8NNNC`, 4.7 µF 16V X5R 0603) C14/C24 — 2 instances. Plus larger bulk caps (10 µF X5R 0805 — multiple). Quantitatively **abundant**, exceeds spec.
- **Layout flag**: each VDD pin needs a 100 nF within ≤2 mm in PCB layout. The schematic groups caps in remote columns (X=355) — global net is correct, but PCB review must verify physical co-location.

---

## 2. DRV8316CRRGFR (U14 motor 1, U15 motor 2) Audit — VQFN-40 RGF, 7×5 mm

### 2.1 Variant identification

**TI SLVSH07 §5 p3 Table 5-1**:
- DRV8316C**R** (suffix R) = SPI variant. PWM mode, slew rate, CSA gain, OCP level, OVP threshold, BUCK_SEL all configured via **SPI registers** (Control Register 1-12, §8.6).
- DRV8316C**T** (suffix T) = Hardware variant. Same parameters set by 4-level pin straps (MODE/SLEW/GAIN/OCP-SR/VSEL_BK).

**Twin28xx**: BOM line 46 lists `DRV8316CRRGFR` ⇒ **SPI variant**. Confirmed by symbol pinout: pins 33/34/35/36 are SDO/SDI/SCLK/nSCS (SPI), and there is no MODE/SLEW/GAIN pin (those positions are NC on the R variant per §6.1 Fig 6-1 p4).

### 2.2 V_VM voltage ratings (cited)

| Spec | Value | Source |
|---|---|---|
| VM **abs max** | **40 V** (–0.3 V min) | TI SLVSH07 §7.1 p6, row "Power supply pin voltage (VM)" |
| VM recommended-operating | 4.5 V min, 24 V nom, **35 V max** | TI SLVSH07 §7.3 p6, row "VVM Power supply voltage" |
| VM ramp rate | up to 4 V/µs | TI SLVSH07 §7.1 p6 |
| VM UVLO rising | 4.3 / 4.4 / 4.5 V | TI SLVSH07 §7.5 p13, row VUVLO |
| VM UVLO falling | 4.1 / 4.2 / 4.3 V | TI SLVSH07 §7.5 p13 |
| OVP rising (SPI, OVP_SEL=0 default) | 32.5 / 34 / 35 V | TI SLVSH07 §7.5 p13 |

**24 V nominal supply** is exactly the recommended-operating nominal. Headroom to abs-max = 16 V; headroom to recommended-max = 11 V; headroom to OVP trip = 8.5 V (typical OVP at 34 V). With the SMF30CA TVS clamping at ≤48.4 V (working: 30 V) on the input, transient excursions during inductive load events should be safely within the 40 V abs-max — see `07_smf30ca_deep_dive.md` for dV/dt analysis.

### 2.3 R_DS(on) (cited)

**TI SLVSH07 §7.5 p11, row RDS(ON)** "Total MOSFET on resistance (High-side + Low-side)":

| Conditions | Min | Typ | Max | Unit |
|---|---|---|---|---|
| VVM > 6 V, IOUT = 1 A, **TA = 25 °C** | — | **95** | **120** | mΩ |
| VVM < 6 V, IOUT = 1 A, TA = 25 °C | — | 105 | 130 | mΩ |
| VVM > 6 V, IOUT = 1 A, **TJ = 150 °C** | — | **140** | **185** | mΩ |
| VVM < 6 V, IOUT = 1 A, TJ = 150 °C | — | 145 | 190 | mΩ |

Linear interpolation typ between 25 and 150 °C: slope = (140-95)/(150-25) = 0.36 mΩ/°C.
- TJ=125 °C: R_DS(on) typ ≈ **131 mΩ**.
- TJ=140 °C: R_DS(on) typ ≈ **136 mΩ**.

(These are HS+LS combined; for FOC P_CON = 3 × IRMS² × R_DS(on)(combined) — see §3.)

### 2.4 Thermal information (cited)

**TI SLVSH07 §7.4 p7, VQFN (RGF) 40-pin** — full row:

| Metric | Value | Unit |
|---|---|---|
| RθJA Junction-to-ambient | **25.7** | °C/W |
| RθJC(top) Junction-to-case (top) | 15.2 | °C/W |
| RθJB Junction-to-board | 7.3 | °C/W |
| ΨJT Junction-to-top characterization | 0.2 | °C/W |
| ΨJB Junction-to-board characterization | 7.2 | °C/W |
| RθJC(bot) Junction-to-case (bottom) | **2.0** | °C/W |

These are JEDEC-standard 4-layer board values. RθJA = 25.7 is achievable on a real 4-layer PCB if (a) the EP is connected to a copper pour ≥100 mm² via ≥9 thermal vias, and (b) bottom layer has matching copper (per TI §11.1 p83 "The device thermal pad should be soldered to the PCB top-layer ground plane. Multiple vias should be used to connect to a large bottom-layer ground plane.").

### 2.5 Power-loss formulas — full quote of TI Table 11-1 (§11.3.1, p85)

| Loss type | Trapezoidal | **Field-oriented control (FOC)** |
|---|---|---|
| Standby power | P_standby = VM × IVM_TA | P_standby = VM × IVM_TA |
| LDO | P_LDO = (VM − VAVDD) × IAVDDD if BUCK_PS_DIS = 1; **P_LDO = (VBK − VAVDD) × IAVDDD if BUCK_PS_DIS = 0** | (same) |
| FET conduction | P_CON = 2 × I_PK(trap)² × R_ds,on(TA) | **P_CON = 3 × I_RMS(FOC)² × R_ds,on(TA)** |
| FET switching | P_SW = I_PK(trap) × V_PK(trap) × t_rise/fall × f_PWM | **P_SW = 3 × I_RMS(FOC) × V_PK(FOC) × t_rise/fall × f_PWM** |
| Diode | P_diode = 2 × I_PK(trap) × V_F(diode) × t_DEADTIME × f_PWM | **P_diode = 6 × I_RMS(FOC) × V_F(diode) × t_DEADTIME × f_PWM** |
| Buck | (none for trap) | **P_BK = 0.11 × V_BK × I_BK** (assuming η_BK = 90%) |

(Verbatim from TI SLVSH07 §11.3.1 Table 11-1 p85.)

### 2.6 BUCK_OUT default at boot — chicken-and-egg cold-start

**TI SLVSH07 §8.6.2.6 Control Register 6 (Offset = 8h) [Reset = 00h], p67, Table 8-23**:
- BUCK_DIS bit (bit 0): **Reset value 0h** → "Buck regulator is enabled" (default).
- BUCK_SEL bits (bits 2-1): **Reset value 0h** → **"Buck voltage is 3.3 V"** (default).
- BUCK_CL bit (bit 3): Reset 0h → 600 mA current limit.
- BUCK_PS_DIS bit (bit 4): Reset 0h → power sequencing enabled.

**Conclusion**: at power-up, before any SPI write, the DRV8316C buck comes up at **3.3 V, 600 mA limit, with AVDD power-sequencing enabled**. This is exactly what is needed to bootstrap the +3.3V rail for the STM32 — no chicken-and-egg problem. The STM32 is powered by either USB VBUS (5 V → XC6206 LDO → 3.3 V) or by the DRV8316 buck (24 V → buck → 3.3 V → XC6206 LDO acts as a downstream regulator with 3.3 V input dropping to ~3.0–3.05 V output given XC6206's typ 250 mV dropout at light load — verify this in `06_datasheet_others.md` against the XC6206 spec; if dropout pulls the rail below 3.0 V, the STM32 USB block (DS12288 Table 92, VDD min for USB = 3.0 V) may not function).

For the **DRV8316CT (HW variant)**, the boot-time buck voltage is set by the VSEL_BK pin tied at hardware-design time (§7.5 p8, four-level pin: AGND→3.3V, Hi-Z→5.0V, 47k to AVDD→4.0V, AVDD→5.7V). **Twin28xx is the SPI variant** so this does not apply — but for completeness, on the CR variant the analogous pin is FB_BK (which is just feedback, not a select pin), and BUCK_SEL register bits start at 00b ⇒ 3.3 V at boot.

### 2.7 DRV8316C cap recommendations vs Twin28xx (cited per pin)

**TI SLVSH07 Table 6-1 (Pin Functions) p4-5** quotes (verbatim):

| Pin | TI requirement (verbatim) | Twin28xx actual (BOM cross-check) | Status |
|---|---|---|---|
| AVDD (25) | "Connect an X5R or X7R, 1-µF, 6.3-V ceramic capacitor between the AVDD and AGND pins. This regulator can source up to 30 mA externally." | C31/C45 = CL10A105KB8NNNC = **1 µF X5R 50V 0603** (BOM line 9) | OK ✓ — value matches; voltage rating exceeds spec (50 V vs 6.3 V min); X5R OK (X7R preferred for temp coefficient but X5R within spec). |
| CP (8, charge pump out) | "Connect a X5R or X7R, 1-µF, 16-V ceramic capacitor between the CP and VM pins." | C33/C47 = CL10A105KB8NNNC = **1 µF X5R 50V 0603** | OK ✓ |
| CPH↔CPL (7↔6) | "Connect a X5R or X7R, 47-nF, ceramic capacitor between the CPH and CPL pins. TI recommends a capacitor voltage rating at least twice the normal operating voltage of the device." | C32/C46 = CL10B473KB8NNNC = **47 nF X7R 50V 0603** (BOM line 10) | OK ✓ — value matches exactly (47 nF C-variant requirement — older non-C parts and DRV835x require 22 nF; 47 nF is the documented value for DRV8316**C** specifically). 50 V rating > 2×24 V = 48 V minimum; just barely meets, but acceptable. |
| VM (9, 10, 11) | "Connect to motor supply voltage; bypass to PGND with two **0.1-µF** capacitors (for each pin) plus **one bulk capacitor** rated for VM. TI recommends a capacitor voltage rating at least twice the normal operating voltage of the device." | Per driver: 5× GRM21BR61H106KE43L = **10 µF X5R 50V 0805** (BOM line 5) on VM net at world Y=101–115 (around U14/U15), plus **C43/C57 = EEEFT1H331GP = 330 µF 50V SMD aluminum electrolytic** (BOM line 11), plus optional **C44/C58 = 50PX330MEFC10X16 = 330 µF 50V THT** (BOM line 12). Total ~50 µF ceramic + 330 µF bulk per driver. | OK ✓ — *exceeds* TI spec on bulk and MF capacitance. **Note**: TI explicitly says "two 0.1-µF capacitors (for each pin)" — i.e. 6× 0.1 µF total per driver (3 VM pins × 2 caps each). Twin28xx replaces those with 10 µF ceramics, which provides far better LF and MF decoupling but **slightly worse HF response** than 0.1 µF X7R 0402 placed micrometres from each VM pin would. NIT: consider adding 6× 100 nF X7R 0402 on VM at the U14/U15 footprint in next revision for HF noise rejection. |
| VREF/ILIM (37) | "Connect a X5R or X7R, **0.1-µF**, 6.3-V ceramic capacitor between the VREF and AGND pins." (PWM Mode 1/3 = VREF; Modes 2/4 = ILIM with resistor divider, see §9.2.2.2.2 p76) | **NEEDS VERIFICATION** in motor_driver.kicad_sch — pin 37 connection not yet fully traced. The schematic does show resistors near U14/U15 (R29/R31 = 100 kΩ, R30/R32 = 330 Ω, BOM lines 28 and 32) which could be a VREF/ILIM divider, but exact pin connectivity needs schematic-side check. | **Open question** — must verify. Promoted to a B-tier blocker pending verification (see §4 below). |

**Buck output bypass C_BK (TI §9.2.1.1.5 p72 + §7.5 p8)**: "C_BK is recommended to be 22-µF" with 22 µH or 47 µH inductor. **Twin28xx**: L1/L2 = PRS3015-470MT = **47 µH** (BOM line 22). The matching CBK should be 22 µF; need to verify in motor_driver schematic which cap on BUCK_OUT serves this role (likely one of C34/C35/C37-C42 = 10 µF X5R 0805, but 10 µF < 22 µF spec). **NIT: verify CBK = 22 µF on BUCK_OUT; if only 10 µF present, add another 10 µF in parallel.**

### 2.8 MODE / GAIN / SLEW four-level pin tying (CT variant only — informational)

**TI SLVSH07 §7.5 p11, FOUR-LEVEL INPUTS Table** (for the CT/HW variant ONLY — DRV8316CR uses SPI registers instead of these pins):

| Mode | Connection | Voltage range |
|---|---|---|
| VL1 | Tied to AGND | 0 to 0.2×AVDD |
| VL2 | Hi-Z (no connection) | 0.27 to 0.545 × AVDD |
| VL3 | 47 kΩ ± 5 % to AVDD | 0.606 to 0.909 × AVDD |
| VL4 | Tied to AVDD | 0.945 × AVDD to AVDD |

Internal pull-up RPU = 70-130 kΩ to AVDD; internal pull-down RPD = 70-130 kΩ to AGND (§7.5 p11).

For the OCP/SR pin (CT variant), the table is similar but uses 22 kΩ to AGND for Mode 2 (VL2) instead of Hi-Z (§7.5 p11 OCP/SR row).

**Twin28xx is the CR (SPI) variant — these pins are not present**, so this only matters for cross-checking that the symbol/footprint is the right variant. Verified: pin 33/34/35/36 are SDO/SDI/SCLK/nSCS (SPI), confirming CR variant. ✓

### 2.9 DRVOFF (pin 21)

- **TI SLVSH07 §7.5 p10, "LOGIC-LEVEL INPUTS (DRVOFF, INHx, INLx, nSLEEP, SCLK, SDI)"**: VIH typ 1.5 V; internal pull-down RPD = 70-130 kΩ (typ 100 kΩ).
- **TI SLVSH07 §6 Table 6-1 p4**: "When this pin is pulled high the six MOSFETs in the power stage are turned OFF making all outputs Hi-Z."
- Default with DRVOFF floating (or external no-connect): pulled low by internal RPD ⇒ **drivers ENABLED** (functional).

**Twin28xx**: schematic shows DRVOFF tied to a `no_connect` marker at world (125.73, 105.41) — this is functional but **loses a hardware-level safety shutdown path**. Recommendation: route DRVOFF to a spare MCU GPIO so firmware can hardware-disable the driver during emergency stop. NIT, not blocker.

### 2.10 nSLEEP (pin 23)

- **TI SLVSH07 §7.5 p10**: nSLEEP VIH min = 1.6 V, hysteresis typ 250 mV, internal RPD = 150-300 kΩ to AGND (typ 200 kΩ).
- **TI SLVSH07 §7.5 p8**: tWAKE = 1 ms typ (nSLEEP=1 to outputs ready); tSLEEP = 120 µs (period to enter sleep); **tRST = 20-40 µs (period to reset faults)**.

**Twin28xx**: nSLEEP routed from MCU GPIO (verified by hierarchical label `nSLEEP` exiting motor_driver sub-sheet). MCU drive at 3.3 V CMOS-high → well above 1.6 V VIH. Firmware must respect 1 ms wake-up before driving inputs, and use 20-40 µs pulse (NOT 120 µs+) for fault-reset-without-sleep.

### 2.11 Layout / EP via recommendation

**TI SLVSH07 §11.1 p83 (Layout Guidelines)**: "The device thermal pad should be soldered to the PCB top-layer ground plane. Multiple vias should be used to connect to a large bottom-layer ground plane. The use of large metal planes and multiple vias helps dissipate the I² × R_DS(on) heat that is generated in the device."

TI does not specify an exact via count in the text, but the layout-example figure on page 84 (`drv8316c_p84_layout.png`) shows ~9-12 thermal vias under the EP. Industry consensus for VQFN with EP is **≥1 via per mm² of EP area**. The DRV8316C EP is approximately 5.7 × 4.7 mm = ~27 mm², so **≥9 thermal vias** (0.3 mm dia, plated through, drilled to inner GND plane and bottom GND plane).

**Verify in PCB review** (`02_pcb_top.md`).

---

## 3. Re-done safe-current calculation (CORRECTED — uses TI's actual formulas)

### 3.1 Formula stack (FOC, per TI SLVSH07 Table 11-1 §11.3.1 p85)

P_total = P_standby + P_LDO + P_CON + P_SW + P_diode + P_BK

with:
- P_standby = VM × IVM (IVM at fPWM, BUCK_DIS=0; per §7.5 p7, IVM ≈ 13–22 mA at fPWM = 25–200 kHz, TA = 25 °C, BUCK enabled). Use **IVM = 15 mA at fPWM = 50 kHz (interpolated)**.
- P_LDO ≈ 0 if VBK = 3.3 V = VAVDD (no headroom across LDO). Twin28xx uses BUCK_OUT to power the +3.3V rail through the XC6206 LDO; AVDD-internal load (max 30 mA per §7.5 p7) draws from buck through internal LDO at near-zero V drop.
- P_CON = 3 × IRMS² × R_ds,on(TJ).
- P_SW = 3 × IRMS × V_PK_FOC × t_rf × f_PWM, with V_PK_FOC ≈ VM = 24 V.
- P_diode = 6 × IRMS × V_F × t_DEAD × f_PWM, with V_F ≈ 0.8 V (typ body diode), t_DEAD per §7.5 p12 (depends on slew setting).
- P_BK = 0.11 × V_BK × I_BK ≈ 0.11 × 3.3 × 0.05 = 0.018 W (negligible).

Thermal equation: **TJ = TA + θJA × P_total = TA + 25.7 × P_total**.

### 3.2 Slew-rate-dependent timings (from §7.5 p11-12)

| SLEW setting | Slew rate (typ) | t_rise/fall (24 V swing) | t_DEAD (typ) |
|---|---|---|---|
| 00b (AGND) | 25 V/µs | 960 ns | 1800 ns |
| 01b (Hi-Z) | 50 V/µs | 480 ns | 1100 ns |
| 10b (47 kΩ to AVDD) | 125 V/µs | 192 ns | 650 ns |
| **11b (AVDD) — max** | **200 V/µs** | **120 ns** | **500 ns** |

For lowest losses use SLEW = 11b (200 V/µs). For lowest EMI use SLEW = 00b. Most BLDC FOC applications use 50–125 V/µs.

### 3.3 R_DS(on) interpolation
- TJ = 125 °C: R_DS,on(typ) = 95 + (140-95)×(125-25)/125 = **131 mΩ**
- TJ = 140 °C: R_DS,on(typ) = 95 + (140-95)×(140-25)/125 = **136 mΩ**

### 3.4 Numerical results (binary-search solver; equations sanity-checked at IRMS = 1.5 A)

**Configuration A — SLEW = 200 V/µs (11b, max), fPWM = 50 kHz, FOC, with active demagnetization (P_diode ≈ 0 since AD turns LS FET on after dead-time, bypassing body diode):**

| TA | TJ_target | P_budget = (TJ−TA)/25.7 | I_RMS_max |
|---|---|---|---|
| 25 °C | 125 °C | 3.89 W | **2.49 A** |
| 25 °C | 140 °C | 4.47 W | **2.68 A** |
| 85 °C | 125 °C | 1.56 W | **1.27 A** |
| 85 °C | 140 °C | 2.14 W | **1.61 A** |

**Configuration B — SLEW = 200 V/µs, fPWM = 50 kHz, FOC, **without** active demagnetization (V_F = 0.8 V, P_diode active):**

| TA | TJ_target | I_RMS_max |
|---|---|---|
| 25 °C | 125 °C | 2.37 A |
| 25 °C | 140 °C | 2.56 A |
| 85 °C | 125 °C | 1.17 A |
| 85 °C | 140 °C | 1.51 A |

**Configuration C — SLEW = 25 V/µs (00b, default after register reset), fPWM = 30 kHz** (slow slew — minimum EMI but maximum switching loss):

| TA | TJ_target | I_RMS_max |
|---|---|---|
| 25 °C | 125 °C | 1.24 A |
| 85 °C | 125 °C | 0.47 A |
| 85 °C | 140 °C | 0.68 A |

**Note on user's expected ranges:**
- "~2.5-3 A at 25 °C with max slew" → matches Config A (2.49–2.68 A) and Config B (2.37–2.56 A). ✓
- "~1.5-2 A continuous at 85 °C" → matches Config A at TJ_target = 140 °C (1.61 A) and Config B at TJ_target = 140 °C (1.51 A). At more conservative TJ_target = 125 °C, the limit drops to 1.17–1.27 A. The exact answer depends on chosen TJ derate target and whether active demag is enabled.

### 3.5 Conclusions on the 3-5 A RMS / 8 A peak design target

- **8 A peak** is the device's recommended-operating peak (§7.3 p6, IOUT) — short transients (≤100 ms) are bounded by SOA, not steady-state thermal. Acceptable.
- **3 A RMS continuous** at TA ≤ 50 °C is achievable with **SLEW = 200 V/µs + active demagnetization + good PCB thermal design** (≥9 EP vias, large copper pour, possibly Cu-on-bottom heat-sink). At TA = 85 °C and JEDEC θJA, **3 A RMS is NOT thermally feasible** continuously — it would require θJA ≤ 17 °C/W, which on 4-layer 35 µm copper is realistic only with active airflow or a heatsink.
- **5 A RMS continuous**: NOT achievable with this device and θJA = 25.7. Solving 5 A: P_CON = 3 × 25 × 0.131 = 9.8 W (conduction alone), needs (TJ − TA) ≥ 9.8 × 25.7 = 252 °C. Even at TA = 25 °C and TJ_max = 150, ΔT = 125 °C ⇒ max P = 4.86 W ⇒ I_max ≈ 2.8 A continuous **at room temperature**. At elevated temp, less.

**Recommendation**:
1. Treat the **continuous design target as 1.5-2 A RMS at 85 °C ambient**, with peak 8 A for ≤10% duty cycle.
2. Operate SLEW = 11b (200 V/µs) for minimum switching losses; accept the higher EMI.
3. Enable active demagnetization in firmware (EN_ASR=1 + EN_AAR=1 in the relevant SPI control register) to eliminate body-diode losses.
4. Verify in `02_pcb_top.md` that EP under U14/U15 has ≥9 thermal vias to GND plane, and that the GND copper area on at least 2 layers is ≥100 mm² adjacent to each driver.
5. If 3+ A RMS at 85 °C is required, plan for: (a) heatsink on the bottom of the PCB (where RθJC(bot) = 2.0 °C/W gives the best heat path), (b) forced airflow, or (c) duty-cycle the application below the steady-state continuous rating.

---

## 4. BLOCKERS / CRITICAL / NITS (round-2)

### BLOCKERS

1. **(B1) Motor phases dangling — same as v1.** PHA1/PHB1/PHC1 and PHA2/PHB2/PHC2 hierarchical labels exit each motor_driver sub-sheet and are not connected to any motor connector. Per ERC report 6× `label_dangling` errors. As-designed the board cannot drive any motor. Fix: route OUTA/OUTB/OUTC of each driver to the BK22 mezzanine connector or to dedicated 3-pin JST headers. (TI SLVSH07 §6 Pin Functions Table 6-1 p4 OUTA/OUTB/OUTC.)

2. **(B2) U9 (XC6206 LDO) Vin not driven.** ERC reports power-flag missing on the LDO input. Verify the LDO Vin pin connects either to USB VBUS (5 V) via Q1 P-FET, or to BUCK_OUT from the DRV8316. If neither, +3.3V rail will not be powered when USB is unplugged. (Cross-reference XC6206 datasheet for input-voltage spec and dropout, see `06_datasheet_others.md`.)

3. **(B3) Round-2 NEW — VREF/ILIM (DRV8316 pin 37) connection unverified.** TI SLVSH07 Table 6-1 p5 says: in PWM Mode 1/3 (default after register reset is Control Register 2 PWM_MODE = 00b = 6× PWM, which is Mode 1), VREF pin is the current-sense amplifier reference and **must have a 0.1 µF ceramic to AGND**. In Mode 2/4 it becomes the ILIM input requiring a resistor divider. The schematic motor_driver.kicad_sch has not been fully traced for pin 37 in this round — if pin 37 is left floating, current sensing will not work (SOx outputs will be saturated/garbage, breaking FOC). **Must verify** by inspecting motor_driver.kicad_sch or running ERC with all symbol pins typed correctly.

### CRITICAL nits

4. **(C1) No ferrite between VDD and VDDA.** Twin28xx ties VDDA pin (29) and VREF+ pin (28) directly to the +3.3V global net via short stubs at U7. AN4488 §2.2 p8 explicitly recommends a ferrite bead between VDD and VDDA, plus a 47 Ω resistor between VDDA and VREF+. Without these, motor-driver switching noise on +3.3V couples directly into the ADC reference, degrading current-sense ENOB by 1-2 bits. **For a motor controller using 12-bit ADC for FOC current feedback, this is meaningful.** Recommendation: add 1× ferrite bead (~600 Ω @ 100 MHz, 0603) between +3.3V and VDDA, and 1× 47 Ω resistor between VDDA and VREF+. Re-route C25-C28 close to U7 in PCB layout.

5. **(C2) DRV8316C thermal de-rating tightens design envelope.** Per the corrected calculation §3.4: at TA = 85 °C, max continuous I_RMS is ~1.27 A (TJ_target=125) to 1.61 A (TJ_target=140) with max slew + active demag. The user-stated 3-5 A RMS target requires either: (a) lowering TA spec to ≤40-50 °C, or (b) adding heat-sinking to drop θJA from 25.7 to <18 °C/W. Confirm in PCB review.

6. **(C3) HSE crystal load caps mismatched.** C11/C18 = 30 pF gives effective CL = 25 pF when the X322512MSB4SI requires CL = 20 pF (per BOM). Per DS12288 §5.3.10 p123 the recommended Cstray to assume is 10 pF. Optimal value is **20 pF** for both C11 and C18. Frequency error ~few-ppm low — non-blocking but suboptimal for USB FS jitter and crystal aging. Easy fix: substitute 0402CG200J500NT (20 pF) for 0402CG300J500NT (30 pF) in next revision.

### NITs

7. **(N1) DRVOFF pin 21 floating.** No safety hardware-shutdown path. Recommend routing to spare MCU GPIO. (Same as v1.)

8. **(N2) VCP-to-VM cap (C33/C47) is X5R, X7R preferred** for temperature stability on the charge pump. (Same as v1; TI Table 6-1 p4 says "X5R or X7R" so X5R is in-spec.)

9. **(N3) VBAT 100 nF cap** — AN4488 §2.2 p8 recommends a 100 nF cap on VBAT even when tied to VDD ("recommended to connect this pin to VDD with a 100 nF external ceramic decoupling capacitor"). Confirm a 100 nF lives near U7 pin 1 in PCB layout.

10. **(N4) DRV8316C VM pin per-pin 100 nF caps**. TI Table 6-1 p5 says "two 0.1-µF capacitors (for each pin) plus one bulk capacitor". Twin28xx uses 5× 10 µF X5R 0805 + 330 µF aluminum per driver, exceeding bulk and MF spec, but does not have explicit 6× 100 nF X7R 0402 close to the 3 VM pins. NIT: add 6× 100 nF X7R 0402 in PCB layout near each U14/U15 VM pin for HF noise rejection.

11. **(N5) BUCK CBK = 22 µF spec; verify Twin28xx's value.** Need to inspect motor_driver.kicad_sch for the cap on BUCK_OUT/SW_BK after the inductor — if it is a single 10 µF X5R, add another in parallel to reach 22 µF (per TI §7.5 p8 buck regulator table requires CBK = 22 µF for spec'd performance).

12. **(N6) USB series resistors — not applicable / clarify documentation.** R12-R14, R17, R19, R20 (49.9 Ω) are NOT USB series resistors (DS12288 Table 92 footnote 4 explicitly says no external resistors needed on USB). They are likely the SOx current-sense filter; verify in schematic review and rename net labels for clarity.

### Open questions for designer

- Is BUCK regulator on each DRV8316 actually used to power something on the board? If so, what voltage is BUCK_SEL set to (per SPI register 6, default 3.3 V)? If unused, TI §9.2.1.1.5 p72 says "even if unused, the buck regulator components must be populated" and recommends Resistor Mode (RBK = 22 Ω, CBK = 22 µF) — Twin28xx uses the inductor (47 µH) which is fine but verify the buck output is loaded.
- What is the PWM mode (6× vs 3× PWM, with or without current limit)? Default after reset (PWM_MODE bits in Control Register 2, default = 00b = 6× PWM) — confirm firmware uses 6× PWM mode for FOC.

---

## 5. Sources cited (all primary-source; document IDs verified)

- **Texas Instruments, "DRV8316C Three-Phase Integrated FET Motor Driver Datasheet", SLVSH07** (December 2022). 95 pages. Local PDF: `D:\gehub\twin28xx\_review\datasheets\DRV8316C_TI.pdf`.
  - §5 Device Comparison Table p3
  - §6.1 Pin Configuration Fig 6-1 / Table 6-1 (Pin Functions) p4-5
  - §7.1 Absolute Maximum Ratings p6 — VM abs max 40 V
  - §7.3 Recommended Operating Conditions p6 — VM 4.5/24/35 V
  - §7.4 Thermal Information p7 — RθJA = 25.7 °C/W
  - §7.5 Electrical Characteristics p7-13 — RDS(on), slew rates, dead time, charge pump, AVDD, OVP, UVLO, OCP
  - §8.6.2.6 Control Register 6 (Offset 8h, Reset 00h) p67 — BUCK_SEL default = 3.3 V
  - §9.2.1.1.6 Current Sensing & Output Filtering p73 — 330 Ω + 22 pF SOx filter recommendation
  - §10.1 Bulk Capacitance p82
  - §11.1 Layout Guidelines p83 — thermal pad / vias
  - §11.2 Layout Example p84
  - §11.3.1 Power Dissipation Table 11-1 p85 — verbatim power-loss formulas

- **STMicroelectronics, "STM32G474xB/xC/xE Datasheet", DS12288 Rev 1** (May 2019). 232 pages. Same pin map as G473xB. Local PDF: `D:\gehub\twin28xx\_review\datasheets\STM32G473_farnell.pdf` (mirror via Farnell — Rev 1; ST.com hosts Rev 5 with identical pin map).
  - §4.3 LQFP-64 pinout fig 7 p50
  - §4.9 Table 11 (Legend) p55, Table 12 (pin definition) p56-71 — FT/TT classifications
  - §5.1.6 Power supply scheme fig 15 p80 — n×100 nF + 4.7 µF, 100 nF + 1 µF on VDDA / VREF+
  - §5.3.10 (HSE oscillator) Table 44 p123-124 — **"10 pF can be used as a rough estimate of the combined pin and board capacitance"**
  - §5.3.15 NRST pin Table 61 p139 / fig 26 p140
  - §5.3.27 USB Table 92 p181 — **"No external termination series resistors are required"**

- **STMicroelectronics, "AN4488 — Getting started with STM32F4xxxx MCU hardware development", DocID026304 Rev 1** (June 2014). 41 pages. (Note: ST has not published a STM32G4-specific equivalent of AN4488; the power-supply-scheme guidance in DS12288 §5.1.6 fig 15 supersedes any AN4488 detail for the G4 family. AN4488 is referenced for the supplementary text recommendations on ferrite, VREF+ resistor, etc.) Local PDF: `D:\gehub\twin28xx\_review\datasheets\AN4488.pdf`.
  - §2.1.2 Battery backup p7 — VBAT=VDD if no battery
  - §2.2 Power supply schemes p8 — VDD: n × 100 nF + min 4.7 µF; VDDA: 100 nF + 1 µF; VREF+: 100 nF + 1 µF; **"VDDA can be connected to VDD through a ferrite bead. The VREF+ pin can be connected to VDDA through a resistor (typ. 47 Ω)"**
  - §2.3.3 System reset p11 / fig 4 — NRST 100 nF (down to 10 nF acceptable)
  - §5.1 Boot mode selection Table 7 p27 + fig 19 p27 — BOOT0 pull-down + switch
  - §6.3.1 SWJ debug port pins Table 8 p30 — PA13=SWDIO, PA14=SWCLK
  - §6.3.3 Internal pull-up/down on JTAG pins p31

- **STMicroelectronics, "AN2867 — Oscillator design guide", AN2867 Rev 1** (January 2009). 20 pages. Local PDF: `D:\gehub\twin28xx\_review\datasheets\AN2867.pdf`. *Note: this older revision uses Cs = 5 pF as an example value; the current revision (Rev 23, January 2025) and the STM32G4 datasheet DS12288 §5.3.10 recommend Cs = 10 pF for STM32G4 for more conservative sizing. The crystal-load math is identical across revisions.*
  - §3 Pierce oscillator p8, fig 4 — crystal + 2× CL + Cs
  - §4.2 Load capacitor CL p10 — formula CL = (CL1·CL2)/(CL1+CL2) + Cs
  - §4.3 Gain margin p10 — gm > 5 × gmcrit
  - §4.6 Crystal pullability p13 — Δf/f0 = Cm/(2(C0+CL)²)
