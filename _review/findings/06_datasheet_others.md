# 06 Datasheet Review — Discrete & Support ICs (Pre-Fab) — v2 (primary-source verified)

Twinspora dual-BLDC motor controller. Inputs: 24 V via BK22 mezzanine; USB-C 5 V VBUS; CAN-FD on J7/J8. This document supersedes `v1_archive/06_datasheet_others.md` and resolves the MT6701 MODE-pin disagreement between `v1_archive/01_schematic.md` (claimed MODE floating defaults to I²C, conflicting with SPI) and `v1_archive/06_datasheet_others.md` (claimed MODE floats and SSI works).

Every datasheet number below has document ID + section/page citation. PDFs were pulled to `_review/datasheets/` for re-verification.

---

## Power-tree — verified against TI SLVSH07 + the `.kicad_sch` source

The DRV8316CR (SPI variant of the U14/U15 motor driver) integrates a **mixed-mode buck regulator** that produces a regulated rail off the +24 V VM input. Reference: TI **DRV8316C, doc SLVSH07 (Dec 2022)**:

- **§ 8.3.4 Step-Down Mixed-Mode Buck Regulator (p. 26)**: "DRV8316CR and DRV8316CT have an integrated mixed-mode buck regulator to supply regulated 3.3-V or 5.0-V power for an external controller or system voltage rail. […] The output voltage of the buck is set by […] **BUCK_SEL bits in the DRV8316CR device (SPI variant)**."
- **§ 8.6.2.6 Control Register 6 (p. 67), Table 8-23**: BUCK_SEL bits [2:1], **Reset = 0h**, decoded as `0h = Buck voltage is 3.3 V`. **Default at power-on is therefore 3.3 V**, not 5 V.
- **§ 7.5 Electrical Characteristics, BUCK REGULATOR (p. 8)**: with LBK = 47 µH and CBK = 22 µF, BUCK_SEL = 01b (5 V) gives 4.6/5.0/5.4 V at 0–200 mA load, requiring VVM > 6 V.
- **§ 7.1 Absolute Maximum Ratings (p. 6)**: VM **abs max = 40 V** (not 35 V — corrects v1).
- **§ 7.3 Recommended Operating Conditions (p. 6)**: VVM 4.5 V (min) / 24 V (nom) / **35 V (max)**.

**Schematic-side verification (file `twinspora.kicad_sch`):**

```
+24V (BK22) ──► U14/U15 DRV8316CR VM
                   └─► internal buck (3.3 V default → 5.0 V via BUCK_SEL=01b) ──► hier-pin BUCK_OUT
                                          (motor_driver.kicad_sch line 4833)
                                          ──► top-sheet labels "BUCK"
                                              (twinspora.kicad_sch lines 19107, 19127, 19927)

USB-C VBUS ──► D2 (1N4148WS) ──► +5V net (anode at VBUS, cathode at +5V; OR-ing diode)

BUCK ──► Q1 AO3401A P-FET (S=+5V, D=BUCK, G=R10 330Ω + R11 10kΩ network)
           └─► +5V (when VBUS absent and BUCK ≥ 5V firmware-configured)

+5V net ──► U9 XC6206P332MR pin 2 (Vin)  [verified at world coord (219.71, 36.83) connecting via wire to +5V power-symbol at (208.28, 29.21) — `twinspora.kicad_sch` lines 14175, 14425, 14675, 33958]
        ──► U8 H5VL10BC TVS clamp
        ──► various decoupling

U9 Vout pin 3 (3.3 V) ──► +3.3V net ──► everything else logic-side
```

**ERC `power_pin_not_driven` for U9 pin 2** (`_review/erc.json`): explained — the +5V net is fed from Q1's drain (a `passive` pin) and from D2's cathode. KiCad cannot identify a `power_out` pin driving +5V, so flags it as a *symbol-library* warning. The net is electrically driven; this is a KiCad ERC artefact, not a real connectivity bug. The schematic also has explicit `PWR_FLAG` placed on the +3.3V output (visible in `_review/s1_3v3.png`).

**Top-sheet annotation `text_box` at (157.48, 26.67)** confirms the design intent: *"200ma LDO / Power OR-ing with PMOS / -PMOS gate VBUS pull-up to prevent reverse current to buck output / -This provides low voltage drop / BUCK starts at 3.3 V default / -Also prioritizes VBUS over BUCK"* (`twinspora.kicad_sch` line 12435). The "BUCK starts at 3.3 V default" matches TI Table 8-23.

**Net result**: the +5V rail droops to whatever (BUCK − 0V + small body-diode drop) is on power-up if VBUS is absent and firmware has not yet flipped BUCK_SEL to 5 V. Default BUCK = 3.3 V → +5V rail will be at ~3.3 V minus body-diode drop ≈ 2.6 V. The XC6206 then runs at Vin ≈ 2.6 V which is below the dropout corner; +3.3V output collapses. **This is a real bring-up bomb** (already called as BLOCKER #3 in v1; reaffirmed here with verified citations).

---

## 1. MT6701QT (U16, U18 — magnetic angle encoder, MagnTek QFN-16-1EP 3×3 mm)

**Datasheets read locally:**
- `_review/datasheets/MT6701_Rev1.8.pdf` (MagnTek, version 1.8, 2022/12 — Chinese)
- `_review/datasheets/MT6701_alt_MT6701QT-STD.pdf` (MagnTek, Rev 1.5, 2021/03 — English)

LCSC C2913974 (`MT6701QT-STD`).

### MODE pin (pin 14) — settles the v1 disagreement

**Pin 14 description (Rev 1.8 § 1.2 QFN-16, p. 4 / Rev 1.5 § 1.2 QFN-16, p. 4):**

> *"MODE / 14 / Digital Input / Built-in 200 KΩ Pull-up Resistor / **ABZ or I2C/SSI Selection**"*

This is a **two-state selector**, not a tri-state nor a divider. The datasheet only enumerates two output personalities for pins 6/7/8: ABZ vs. I²C/SSI shared. The 200 KΩ pull-up means MODE defaults HIGH if floating. Combined with the reference circuits below, the mapping is:

- **MODE = HIGH** (floating, internal pull-up to VDD) → pins 6/7/8 are **I²C/SSI shared** (i.e. SDA/SCL/CSN per Rev 1.8 § 7.1 I/O Pin Configuration table, p. 10).
- **MODE = LOW** (tied to GND) → pins 6/7/8 are **A/B/Z** (ABZ output per Rev 1.8 § 7.1, p. 10; ref schematic Fig. 7 p. 11 shows MODE pin with a dotted ground connection in the ABZ reference circuit).

**Reference circuits in Rev 1.8:**
- **Figure 7 (ABZ output, QFN-16, p. 11)**: pin 14 (MODE) drawn with a dashed-grey line down to a small tee — **tied to GND** in the reference circuit. (See also `_review/datasheets/MT6701_p11_zoom.png` rendered from the PDF.)
- **Figure 18 (I²C reference, QFN-16, p. 20)**: pin 14 (MODE) shown **floating** (only the 200 KΩ internal pull-up is drawn).
- **Figure 23 (SSI reference, QFN-16, p. 24)**: pin 14 (MODE) also **floating**.

So per the manufacturer: **floating MODE = I²C/SSI shared mode is the default**. Within the I²C/SSI mode the master selects per-transaction by toggling the CSN pin (pin 8) — MT6701 acts as I²C slave when CSN stays HIGH at idle and as SSI slave when CSN is pulled LOW (Rev 1.8 § 7.8 SSI Interface, p. 24, "通信起始于CSN的下降沿" / "communication starts at the falling edge of CSN").

**Schematic-side verification (`magnetic_encoder.kicad_sch`)** — both U16 and U18 are instances of the same component-sheet symbol at world (140.97, 102.87) mirror_y. Pin 14 (MODE) sits at world (153.67, 102.87). Tracing the wires:

```
pin 14 (MODE)        (153.67, 102.87)
   ↓ wire (line 2273)
                     (153.67, 83.82)        junction (line 2098)
   ↔ wire (line 2193)
                     (140.97, 83.82)        junction (line 2110)
   ↑ wire (line 2333)
                     (140.97, 77.47)        ← +3.3V power symbol (line 3129)
```

**MODE is hard-tied to +3.3V**. This is electrically the same as the manufacturer "floating + 200K internal pullup" default state (HIGH). The v1_archive `01_schematic.md` claim that MODE was floating was wrong about the wire — there is an explicit short to +3.3V for both encoder instances. Net effect is identical to floating: pins 6/7/8 are in I²C/SSI shared mode.

### Part-number suffixes / ordering

Rev 1.8 § 2 Family Members (p. 5):
- `MT6701QT-STD` — QFN-16, **base part: I2C, SSI; AB=1 PPR; Z=1 LSB; UVW=1 pole-pair; analog 0-360°; CCW = increasing**.
- The bare `MT6701QT` (no suffix) speaks I²C and SSI **out of the box** (factory default register settings select these). ABZ is also available *but at AB=1 pulse-per-rev / Z=1 LSB unless you reprogram the EEPROM* — useless as a quadrature encoder without programming.
- Variants `-A200, -A360, -A400, -A600, -A800, -ACD, -AKD, -AKE` ship with higher AB pulse counts pre-programmed.

The board uses bare `MT6701QT` with no suffix (`magnetic_encoder.kicad_sch` line 3551 `Value "MT6701QT"`, BOM line confirms "MT6701QT" without suffix). For SSI use, this is fine — the 14-bit absolute angle is always available regardless of suffix.

### A / B / Z pin function in each output mode

Rev 1.8 § 7.1 I/O Pin Configuration, QFN-16 table (p. 10):

| Pin | I²C   | SSI  | ABZ | ABZ+UVW | ABZ Differential |
|-----|-------|------|-----|---------|------------------|
| 6   | SDA   | DO   | A   | A       | A                |
| 7   | SCL   | CLK  | B   | B       | B                |
| 8   | CSN   | Z    | Z   | Z       | Z                |

**Schematic wires those pins as `MISO`, `SCK`, `NSS` respectively** (`magnetic_encoder.kicad_sch` lines 2431..2541). For SSI: pin 6 → DO maps to `MISO` (correct), pin 7 → CLK maps to `SCK` (correct), pin 8 → CSN maps to `NSS` (correct).

**Verdict: SSI works. The schematic wiring is correct for SSI operation.** The MCU drives NSS low to start a transfer, clocks 24 bits on SCK (rising-edge launch from MT6701, master captures on falling — Rev 1.8 § 7.8.1, p. 25), and reads 14-bit angle + 4-bit status + 6-bit CRC on MISO. v1's `06` correctly concluded SSI works; v1's `01_schematic.md` claim that SSI was broken because of MODE was wrong.

### Sensing geometry (Rev 1.8 § 6 Magnetic Input Specifications, p. 9)

| Parameter | Min | Typ | Max | Unit | Notes |
|-----------|-----|-----|-----|------|-------|
| Magnet diameter | — | 6.0 | — | mm | Recommended Ø6 mm × 2.5 mm cylindrical, **diametrically magnetised**, 1 pole-pair |
| Magnet thickness | — | 2.5 | — | mm | |
| B_pk at IC surface | 200 | — | 1000 | Gauss | |
| **AG** (magnet-to-IC face air gap) | **0.5** | **1.0** | **2.0** | **mm** | |
| RS (rotation speed) | — | — | 55,000 | RPM | |
| DISP (off-axis) | — | — | 0.3 | mm | |

The QFN-16 is sensed from the **top face of the package** (Rev 1.5 § 1.2 QFN-16, "Sensing Center at Geometry Center" caption on the Top View pinout). Magnet must be centred over the QFN top surface. *Mechanical / housing review item — confirm rotor magnet placement on the assembled product.*

### Recommended copper keepout

The Rev 1.8 datasheet does not specify a copper keepout under the sensor. The only sensing-area constraint is the on-chip "Sensing Center at Geometry Center" indication. Best practice for similar Hall ICs is to avoid large copper pours and via fields directly under the package centre to limit eddy-current and magnetic pinning. **No primary-source keepout dimension available** — needs PCB-review observation against the actual layout, not against a datasheet number.

### VDD spec (Rev 1.8 § 5 Electrical Characteristics, p. 7)

- VDD: 3.0 V (min) / 3.3-5.0 V (typ) / 5.5 V (max), I_DD typ 10 mA / max 14 mA.
- **Abs max VDD = 7 V** (Rev 1.8 § 4 Absolute Maximum Ratings, p. 6).
- ESD HBM ±6 kV, CDM ±1.5 kV.
- Decoupling: 0.1 µF on VDD per Rev 1.8 § 7.2 Reference Circuit (Fig 7, p. 11). Optional 6 V TVS recommended for reliability.

Schematic places C59/C60 = 100 nF (0402) on each encoder's VDD pin — meets the datasheet recommendation. No bulk cap; if buck-rail noise is an issue at the encoder, add 1 µF locally — *NIT*.

### Verdict on MT6701 — settles v1 disagreement

- **The bare `MT6701QT` does support SSI** at full 14-bit resolution.
- **The schematic wiring on A/B/Z → MISO/SCK/NSS is correct for SSI use.**
- **MODE is tied to +3.3V** in the schematic (not floating, but electrically equivalent because the internal 200 KΩ pull-up would have the same effect). Datasheet ABZ ref-circuit Figure 7 explicitly grounds MODE; the chip will run in I²C/SSI shared mode here. SSI works.
- v1's `01_schematic.md` BLOCKER claim ("MT6701 MODE floating powers up in I²C mode incompatible with SPI master") is **wrong on two counts**: (a) MODE is *not* floating, it's tied to +3.3V; (b) "I²C mode" and "SSI mode" share the same MODE state and the master selects between them at the bus level, so SSI is fine.
- v1's `06_datasheet_others.md` MODE-pin verdict ("OK, SSI works as intended") is **right**, but its supporting evidence (citing "200 kΩ pull-up keeps it HIGH = I2C/SSI shared, master picks per CSN") is correct except for the schematic claim that pin 14 is left as a no-connect — **it's not, it's tied high**. Either way the chip behaves identically.

---

## 2. CA-IF1044VD-Q1 (U11 — Chipanalog automotive CAN-FD transceiver, DFN-8 3×3 mm)

**Datasheet read locally:** `_review/datasheets/CA-IF1044VD-Q1.pdf` (Chipanalog 上海川土微电子, doc *CA-IF1044-Q1 Version 1.05, 2023/09/01*, 24 pages).

LCSC C5155979.

> Note: this is **not** a TI part. The TI URL `ti.com/lit/ds/symlink/ca-if1044vd-q1.pdf` returns 404. The Chipanalog "CA-IF1044V" family is a second-source for TI's TCAN1044V-Q1 with similar pinout but different transient/ESD specs and process.

### Pinout — Chipanalog § 5 Pin Function Description (p. 4, Table 5-1, Figure 5-1)

| Pin | Name (V variant) | Type | Description |
|-----|-----------|------|-------------|
| 1 | TXD | Input | Transmit data, internal pull-up to VCC |
| 2 | GND | GND | |
| 3 | VCC | Power | 5 V bus-side supply, 0.1 µF decoupling close to pin |
| 4 | RXD | Output | Receive data, output level referenced to **VIO** |
| 5 | **VIO** | Power | Logic-side level-shift supply (only on 'V' variant — pin 5 is NC on non-V) |
| 6 | CANL | I/O | CAN low |
| 7 | CANH | I/O | CAN high |
| 8 | STB | Input | Standby select. STB high = standby, STB low = normal mode. Internal pull-up to VCC. |

### Supply voltage (Chipanalog § 6.3 Recommended Operating Conditions, p. 5)

| Parameter | Min | Max | Unit |
|-----------|-----|-----|------|
| VCC (5 V bus-side) | 4.5 | 5.5 | V |
| **VIO (logic-side)** | **3.0** | **5.5** | **V** |

Abs max (§ 6.1, p. 5): VCC -0.3 to 7 V; VIO -0.3 to 7 V. Bus voltage CANH/CANL: ±58 V (bus fault tolerance).

### Application notes

- **§ 8.9 VIO Supply (p. 16)**: *"In CA-IF1044V, VIO is provided so logic-side ports can directly connect to the MCU. Internal level shifting converts to the 5 V VCC domain. Supports 3.3 V to 5.0 V logic."*
- **§ 9 Application Information (p. 18)**: Figure 9-2 shows VIO **connected to the MCU's supply rail (3.3 V)**, *not* a GPIO. The text says *"图9-2 给出了CA-IF1044V 版本的典型应用图，VIO 电源与MCU 的电源连接在一起"* ("VIO supply is connected together with the MCU supply").
- **§ 8.10 Operating Modes (p. 16)**, Table 8-5: STB high → standby, STB low → normal mode.

### Schematic check on STB, VIO, VCC

Tracing U11 (CA-IF1044VD-Q1, instance at (311.15, 43.18) — `twinspora.kicad_sch` line 32003):

| Pin | Function | Net | Verdict |
|-----|----------|-----|---------|
| 1 | TXD | `FDCAN_TX` | OK |
| 2 | GND | GND | OK |
| 3 | VCC | **+5V** (verified: pin 3 at world (298.45, 45.72) wires to +5V power-symbol at (290.83, 31.75) — lines 14655, 16615, 16815) | **OK, within 4.5–5.5 V** |
| 4 | RXD | `FDCAN_RX` | OK |
| 5 | **VIO** | `CAN_VIO` net (verified: pin 5 at world (323.85, 48.26) connects to label `CAN_VIO` at (335.28, 48.26)) — `CAN_VIO` is **driven by STM32 GPIO PC4** (label appears at (182.88, 142.24), exactly the location of MCU pin 22 = PC4) | **CRITICAL — see below** |
| 6 | CANL | through R + C19 + ACT1210D + PESD2CAN to J7/J8 | OK |
| 7 | CANH | through R + ACT1210D + PESD2CAN to J7/J8 | OK |
| 8 | STB | tied to GND via the same internal node as the EP (pin 9), through wire (323.85, 40.64)→(326.39, 40.64)→(326.39, 64.77 = GND) | **OK, normal mode forced** |
| 9 | EP | tied to GND alongside STB | OK |

### CRITICAL — VIO driven by GPIO, not by a supply rail

The Chipanalog datasheet § 9 explicitly shows VIO connected to the MCU's logic-supply rail (their Figure 9-2 has VIO and the MCU's 3.3 V Vdd connected together). On Twinspora, **CAN_VIO is driven by GPIO PC4**, which:

1. Requires firmware to drive PC4 high before any CAN traffic. If bootloader / fault state leaves PC4 low or hi-Z, CAN is dead and the transceiver may sit in a degraded state.
2. Backfeeds the GPIO during bus glitches — the VIO pin draws ~125-300 µA in normal mode (§ 6.5, p. 6, IIO row), within GPIO drive capability, but any inrush at startup (capacitor charging on the VIO rail) can momentarily peg the GPIO above the abs-max +0.3 V.
3. Provides no transient protection between VIO and the MCU GPIO — they are the same node.

**Recommendation:** wire VIO to **+3.3V** directly (or via a small ferrite for noise isolation), and re-purpose PC4 if needed. If "wake on bus" remote-wake feature is wanted, then the GPIO control is on the **STB** pin, not VIO. STB is the right pin to make controllable; VIO must be a stable supply.

### Decoupling

Chipanalog § 5 (p. 4): "VCC and GND with 0.1 µF as close to the device as possible". Schematic places C16 (100 nF) and C14 (4.7 µF) on VCC and a 100 nF on VIO (visible in `_review/s1_can.png`). Adequate, assuming VIO actually has a stable supply.

### TXD dominant timeout (§ 8.2, p. 14)

Driver shuts off after TXD held low > t_DTO. Family supports data rates as low as 4 kbps, i.e. roughly 250 µs minimum dominant time before shutdown. Adequate for any sensible CAN-FD use.

---

## 3. ACT1210D-101-2P-TL00 (U12 — TDK common-mode choke for CAN-FD)

**Datasheet read locally:** `_review/datasheets/ACT1210D_TDK.pdf` (TDK file `cmf_automotive_signal_act1210d_en.fm`, dated 2022/09/30, 4 pages).

LCSC C3039743.

### Specifications (TDK datasheet § "Characteristics specification table", p. 1)

| Parameter | Value | Unit |
|-----------|-------|------|
| Common-mode inductance @ 100 kHz | **100 µH (typ.), tolerance +50 / -30 %** | µH |
| DC resistance per line, max | **3.0 Ω** | Ω |
| Insulation resistance, min | 10 | MΩ |
| **Rated current, max** | **115** | **mA** |
| Rated voltage, max | 80 | V |
| Operating temp range | -40 to **+150** | °C (this -101 / -510 part) |
| AEC-Q200 compliant | yes | |

### Verdict

Correct part for CAN-FD common-mode rejection. The AEC-Q200 + 150 °C rating and tighter S-parameter response (§ Sdd21 / Scc21 / Ssd graphs, p. 2) compared to the older ACT1210 series make it the right pick. 115 mA rated current is far more than CAN bus signal currents (a few mA), so safe.

### Placement check

Schematic instance at (341.63, 29.21), `dnp no`, between U11 CANH/CANL and the CAN-bus connectors J7/J8 (`_review/s1_can.png`). The PESD2CAN (U13) sits on the connector side of the choke and the split-termination R+C is on the transceiver side — standard CAN-FD reference layout. **OK** — and the v1 claim that U12 was "DNP / not populated" was incorrect (the dnp flag in the schematic at line 38440 is `no`; the `X` markings inside the symbol body in `s1_can.png` are the schematic-symbol drawing of the coupled inductors, not a do-not-populate marker).

---

## 4. PESD2CAN (U13 — Nexperia bidirectional CAN bus ESD diode, SOT23-3)

**Datasheet read locally:** `_review/datasheets/PESD2CAN.pdf` (Nexperia, *PESD2CAN Product data sheet, Rev 2 — 27 September 2012*, 13 pages).

### Specifications (Nexperia § 6 Characteristics, Table 8, p. 4)

| Symbol | Parameter | Conditions | Min | Typ | Max | Unit |
|--------|-----------|-----------|-----|-----|-----|------|
| **V_RWM** | reverse standoff voltage | per diode (pin 1→3 or 2→3) | — | — | **24** | V |
| I_RM | reverse leakage | V_RWM = 24 V | — | <1 | 10 | nA |
| **V_BR** | breakdown voltage | I_R = 1 mA | **26.2** | 28 | **30.3** | V |
| C_d | diode capacitance | f = 1 MHz, V_R = 0 | — | 25 | 30 | pF |
| **V_CL** | clamping voltage | I_PP = 1 A | — | — | **34** | V |
| V_CL | clamping voltage | I_PP = 5 A | — | — | **41** | V |
| r_dif | differential resistance | I_R = 1 mA | — | — | 300 | mΩ |

ESD: IEC 61000-4-2 contact ±30 kV (§ 5 Limiting values + Table 6, p. 2-3). Bidirectional via two diodes referenced to common cathode (pin 3); pin 1 = cathode 1 (CANH side), pin 2 = cathode 2 (CANL side), pin 3 = common cathode (GND).

### Schematic check

U13 at the CAN connector node, pin 3 (GND) on the GND net, pins 1/2 to CANH/CANL respectively (`_review/s1_can.png`). **OK** — bidirectional / polarity-agnostic, V_RWM = 24 V is the standard pick for 5 V CAN signals (CAN signal swings are 1.5 V — 3.5 V differential, well below V_RWM = 24 V).

---

## 5. SRV05-4A (U6, U10, U17, U19 — multi-channel low-capacitance ESD diode array, SOT-23-6)

**Datasheet read locally:** `_review/datasheets/SRV05-4_DOWO_C2972082.pdf` (Hongjiacheng / DOWO, *SRV05-4*, page 1-3 of 6 — used as a pin-compatible cross-reference to the JEDEC SRV05-4 family).

The schematic does not specify an LCSC code for SRV05-4A; the BOM lists `SRV05-4A` with footprint `Diode:SOT-23-6`. The JEDEC-standard SRV05-4 / SRV05-4A specifications across vendors (onsemi, Semtech, DOWO, ProTek) are largely identical for the four key numbers.

### Specifications (DOWO § 6 Specification, Table 4, p. 3)

| Parameter | Symbol | Condition | Min | Typ | Max | Unit |
|-----------|--------|-----------|-----|-----|-----|------|
| **V_RWM** | Reverse stand-off voltage | — | — | — | **5** | V |
| **V_BR** | Reverse breakdown | I_T = 1 mA | **6** | — | — | V |
| I_R | Leakage at V_RWM | V_RWM = 5 V | — | — | 1 | µA |
| **V_C** | Clamping voltage | I_PP = 1 A, 8/20 µs | — | — | **9** | V |
| V_C | Clamping voltage | I_PP = 4.5 A, 8/20 µs | — | — | **12** | V |
| C_J | Capacitance | I/O to GND, V_R = 0, 1 MHz | — | **0.6** | 0.8 | pF |
| ESD | IEC 61000-4-2 contact | | — | — | **±12 kV** | |
| ESD | IEC 61000-4-2 air | | — | — | **±17 kV** | |

### Pinout — DOWO § 5 Pin Configuration (Table-2, p. 2):

| Pin | Function |
|-----|----------|
| 1 | I/O 1 |
| 2 | GND |
| 3 | I/O 2 |
| 4 | I/O 3 |
| 5 | V_CC (rail-clamp anchor — typically tied to the protected rail, e.g. +5V or +3.3V) |
| 6 | I/O 4 |

The Semtech SRV05-4A version typically has **slightly tighter clamp** (V_C ≤ 6 V at 1 A) and may quote ±15 kV / ±8 kV ESD; same pinout. Without the LCSC part code on the schematic the actual sourced device is whatever the assembler sources to that footprint.

### Per-instance schematic check

| Ref | Location (top sheet / sub) | Connector | Channels used | Notes |
|-----|---------------------------|-----------|---------------|-------|
| **U6** | top sheet (135.89, 46.99) | **J2 USB-C** | D+, D-, CC1, CC2 | 4/4 channels used; **VBUS not protected** — see BLOCKER. |
| **U10** | top sheet (255.27, 210.82) | **J5 (Qwiic / I²C)** | SDA, SCL, +3V3?, GND? | Need to verify pin map; only 4 channels available. |
| **U17, U19** | sub-sheet 4 / 5 (215.9, 102.87 each, `magnetic_encoder.kicad_sch`) | **J11 / J12 6-pin SH1.0 encoder breakouts** | 4 SPI lines (NSS, SCK, MOSI, MISO) — VCC/GND not protected | Acceptable for dev breakouts, NIT. |

### USB-C VBUS coverage — confirmed not protected

Tracing `twinspora.kicad_sch` near U6 and J2: U6 has 4 I/O pins routed to D+/D-/CC1/CC2, plus the SRV05's V_CC pin tied to +5V (the rail-clamp anchor). **VBUS does not pass through U6** — VBUS goes from J2 directly to D2 (1N4148WS) and into the +5V tree. The only VBUS-side protection is the C5/C26 decoupling. **No polyfuse, no VBUS TVS** — same finding as v1, confirmed.

---

## 6. SMF30CA (U5, LCSC C19077519 — 200 W bidirectional TVS, SOD-123FL)

**Datasheet read locally:** `_review/datasheets/SMF30CA_C19077519.pdf` (Hongjiacheng *SMF SERIES 200W Surface Mount TVS, Rev 2.1*, 5 pages).

### Specifications (Hongjiacheng Rev 2.1, page 2 — SMF30CA row of the part-number table)

| Parameter | Value | Unit |
|-----------|-------|------|
| **V_RWM** (reverse standoff) | **30** | V |
| **V_BR min** @ I_T = 1 mA | **33.3** | V |
| **V_BR max** @ I_T = 1 mA | **36.8** | V |
| **V_C** (clamping) @ I_PP, 10/1000 µs | **48.4** | V |
| **I_PP** (peak pulse current) | **4.1** | A |
| I_R (leakage at V_RWM) | 1 | µA |
| Marking (bidirectional "CA") | JK | |

These match the v1 deep-dive (`_review/findings/07_smf30ca_deep_dive.md`) numbers exactly, **all confirmed** against the datasheet.

### Adequacy against the corrected DRV8316C abs-max of 40 V

Re-running the analysis from `07_smf30ca_deep_dive.md` against TI SLVSH07 **§ 7.1 abs-max V_VM = 40 V** (not v1's wrong 35 V):

| Transient magnitude | SMF30CA clamps to | DRV8316C state | Verdict |
|---------------------|-------------------|----------------|---------|
| Steady state 24 V | off (≤ 1 µA) | inside operating range | OK |
| Mild regen, rail at 30 V | off (V_RWM = 30 V) | inside operating range | OK |
| Rail at 33-37 V (V_BR knee) | starts to conduct in mA range | OVP trips at ~37 V (TI § 7.5 VM_OVP, p. 11), motor halts briefly | OK / functional |
| ~1-2 A transient | clamp ~37-40 V | At/at edge of 40 V abs max | **MARGINAL** |
| Full I_PP 4.1 A | **clamp 48.4 V** | **8.4 V over 40 V abs max → silicon damage** | **FAIL** |

**Verdict against the corrected 40 V abs max: SMF30CA is still inadequate at full rated I_PP (clamps 8.4 V over abs-max), but for sub-rated transients ≤ 2 A it stays inside abs max though above the 35 V operating-recommended max.** It is poor protection, not catastrophic. v1's blocker call was based on the wrong 35 V abs-max number; the deep dive (`07_smf30ca_deep_dive.md`) already corrected this and recommended a swap to **SMF24CA (C19077515)** as a same-footprint drop-in fix (clamps to 38.9 V at full I_PP — under 40 V abs max), or **SMAJ26CA (C19077544)** for a footprint-change-cleaner solution.

**Re-verified BLOCKER (downgraded from v1):** the SMF30CA at full I_PP 4.1 A clamps to 48.4 V, which is 8 V over the DRV8316C 40 V abs max. For typical regen / induced transients well below I_PP this is acceptable but offers no protection (off until 33 V). **Recommended action: swap to SMF24CA same-footprint drop-in** — see deep-dive document for the full part-selection rationale.

---

## 7. XC6206P332MR (U9, LCSC C5446 — Torex 3.3 V LDO, SOT-23-3)

**Datasheet read locally:** `_review/datasheets/XC6206P332MR_C5446.pdf` (Torex *XC6206 Series, doc ETR0305_004b*, 17 pages).

### Specifications (Torex doc ETR0305_004b)

- **§ Features (p. 1)**: Maximum Output Current 200 mA (3.0 V type — 3.3 V is comparable); Dropout Voltage 250 mV @ 100 mA (3.0 V type); Maximum Operating Voltage **6.0 V**.
- **§ Absolute Maximum Ratings (p. 3)**: **V_IN abs max = 7.0 V**; output current 500 mA short-duration.
- **§ Electrical Characteristics + chart (p. 4-5)**: Input voltage range 1.8 – **6.0 V**; output 3.3 V ±2 % @ 30 mA load; dropout typ ~250 mV @ 100 mA.
- **§ Pin Configuration (p. 2)**: SOT-23: pin 1 = VSS, pin 2 = VOUT, pin 3 = VIN. (KiCad symbol confirms: pin 1 GND, pin 2 Vin, pin 3 Vout — at lines 9320-9373.)

### Schematic + ERC check

U9 at (229.87, 36.83). Pin 2 (Vin) at world (219.71, 36.83). Wire trail: (219.71, 36.83) → (215.9, 36.83) → (208.28, 36.83) (junction) → (208.28, 29.21) which is the **+5V power symbol** (`twinspora.kicad_sch` lines 14175, 14425, 33958). U9 input is **+5V**, not 24 V — same as v1's claim.

The ERC `power_pin_not_driven` warnings on U9 pin 2 (Vin) and pin 3 (Vout) (`_review/erc.json`) are KiCad library artefacts: the +5V net is fed from Q1's drain (a `passive` pin) and D2's cathode (no `power_out` pin in the path), so KiCad reports it as undriven. The +3.3V net is downstream of U9's Vout (which is `power_out`), so the only true "driven" net there is +3.3V; ERC complains because it can't see who drives +5V upstream. These are not real connectivity bugs — there is also a `PWR_FLAG` placed on the +3.3V output as a workaround.

### Verdict

**Safe** under nominal operation. Edge case: at boot before firmware reprograms BUCK_SEL = 5 V, the +5V rail drops to ~3.3 V (or worse, ~2.6 V after the body-diode/Q1 drop), and U9's dropout (250 mV) means the 3.3 V output collapses below the STM32 brown-out threshold. **This is BLOCKER #3 from v1** — confirmed.

---

## 8. AO3401A (Q1 — Alpha & Omega P-channel MOSFET, SOT-23)

**Datasheet read locally:** `_review/datasheets/AO3401A.pdf` (AOS, *AO3401A 30V P-Channel MOSFET*, 5 pages).

### Specifications

| Parameter | Symbol | Condition | Min | Typ | Max | Unit |
|-----------|--------|-----------|-----|-----|-----|------|
| Drain-source breakdown | BV_DSS | | -30 | | | V |
| Gate-source voltage | V_GS | | | | ±12 | V |
| Continuous drain current @ 25 °C | I_D | | -4 | | | A |
| Gate threshold | V_GS(th) | I_D = -250 µA, V_GS = V_DS | -0.5 | -0.9 | -1.3 | V |
| R_DS(on) @ V_GS = -10 V | R_DS(on) | I_D = -4.0 A | | 41 | 50 | mΩ |
| **R_DS(on) @ V_GS = -4.5 V** | R_DS(on) | I_D = -3.0 A | | **47** | **60** | mΩ |
| R_DS(on) @ V_GS = -2.5 V | R_DS(on) | I_D = -1.0 A | | 60 | 85 | mΩ |
| Body-diode V_SD | V_SD | I_F = -1 A | | -0.7 | -1 | V |

(AOS datasheet § Electrical Characteristics, p. 2)

### Role on Twinspora

Q1 in the +5V OR-ing tree (`_review/s1_3v3.png`):
- Source = +5V net
- Drain = BUCK net (the DRV8316 buck output)
- Gate driven by R10 (330 Ω) + R11 (10 kΩ) network referenced to VBUS / GND

Topology: **PMOS body-diode is forward-biased from BUCK to +5V whenever BUCK > +5V + V_SD**. When VBUS is present (5 V), it raises +5V via D2 (1N4148WS); the gate of Q1 is held high (close to VBUS), so V_GS ≈ 0 → P-FET off → no reverse current path from +5V to BUCK. When VBUS is absent, the gate falls (via R11 pull-down to GND), V_GS becomes negative, the FET turns on, BUCK feeds +5V through R_DS(on) ≈ 60 mΩ.

This is a textbook **OR-ing P-FET** circuit, sized very conservatively: -4 A continuous I_D vs. the ~200 mA max load on +5V. **Functional as designed.**

NIT: the gate-discharge path (R11 alone is 10 kΩ to GND) gives an RC time constant with the gate capacitance of ~1.6 nF * 10 kΩ ≈ 16 µs to fully turn the FET on after VBUS removal. During this time, +5V is drawing only from BUCK through Q1's body diode (V_SD ≈ -0.7 V), giving +5V ≈ BUCK − 0.7 V. If BUCK is firmware-set to 5 V, this is fine; if BUCK is at 3.3 V default, +5V drops to 2.6 V and the LDO drops out — same blocker as Q1 + buck-default.

---

## 9. WSD4066DN33 (U4, LCSC C377861 — Winsok Dual N-channel MOSFET, DFN3×3-8L)

**Datasheet read locally:** `_review/datasheets/WSD4066DN_C377861.pdf` (Winsok *WSD4066DN33, Rev 3.0, Jan 2024*, 7 pages).

### Specifications (Winsok Rev 3.0, p. 1-2)

| Parameter | Symbol | Condition | Min | Typ | Max | Unit |
|-----------|--------|-----------|-----|-----|-----|------|
| Drain-source breakdown | BV_DSS | V_GS = 0, I_D = 250 µA | 40 | | | V |
| Gate-source rating | V_GS | | | | ±20 | V |
| Continuous drain current | I_D | T_A = 25 °C | | | 14 | A |
| Pulsed drain current | I_DM | | | | 28 | A |
| **V_GS(th)** | V_GS(th) | V_DS = V_GS, I_DS = 250 µA | **1.0** | **1.5** | **2.0** | V |
| **R_DS(on) @ V_GS = 4.5 V** | R_DS(on) | I_D = 12 A | | **17** | **20** | mΩ |
| R_DS(on) @ V_GS = 10 V | R_DS(on) | I_D = 14 A | | 14 | 17 | mΩ |
| Body diode V_SD | V_SD | I_SD = 1 A, V_GS = 0 | | 0.75 | 1.1 | V |

Pinout (DFN3×3-8L, p. 1): G1 = pin 2, S1 = pin 1, D1 = pins 7,8 (joined). G2 = pin 4, S2 = pin 3, D2 = pins 5,6 (joined). Two independent N-FETs.

### Role on Twinspora

In the POWER IN block alongside U3 (FMMT620 NPN BJT) and U5 (SMF30CA TVS). Per the v1 NIT and the rendered `_review/sheet1_q1.png` and `_review/findings/v1_archive/01_schematic.md` line 50: **back-to-back common-drain N-FET ideal-diode reverse-polarity protection**, with gate boost from the DRV8316 charge pump (VCP). The body diode of one FET passes current during the brief startup window before VCP ramps up; once VCP is up, both FETs conduct fully (R_DS(on) ≈ 17 mΩ × 2 = 34 mΩ total). At 8 A peak this dissipates ~2.2 W, brief-only OK; at 4 A continuous it's ~0.5 W, well within the DFN package thermal envelope.

V_DS = 40 V leaves only ~16 V transient headroom from the 24 V nominal — the SMF30CA TVS (V_C 48 V at full I_PP) can drag the rail above 40 V momentarily, threatening these FETs as well as the DRV8316C.

V_GS(th) = 1 V is low; gate-pull-down/clamp is required to prevent inadvertent turn-on from PWM-induced ringing on the rail. *NIT: confirm the gate has a pull-down or clamping zener visible in the schematic block — the v1 review noted this but didn't verify on layout.*

---

## 10. H5VL10BC (U8, LCSC C20615784 — Hongjiacheng/R+O bidirectional 5 V ESD/TVS, DFN1006-2L)

**Datasheet read locally:** `_review/datasheets/H5VL10BC_C20615784.pdf` (Zhuhai Hongjiacheng *H5VL10BC Bi-directional 5V Low Capacitance ESD, Rev 2.0*, 3 pages).

> Note: BOM lists this as `H5VN10B` but actual placed part marking and LCSC code is `H5VL10BC` — minor naming discrepancy.

### Specifications (Hongjiacheng Rev 2.0, p. 2)

| Parameter | Symbol | Condition | Min | Typ | Max | Unit |
|-----------|--------|-----------|-----|-----|-----|------|
| **V_RWM** | reverse working voltage | bidirectional | — | — | **5.0** | V |
| **V_BR** | breakdown | I_T = 1 mA | **6.0** | — | **9.0** | V |
| I_R | leakage | V_RWM = 3.3 V | — | — | 0.1 | µA |
| **V_C** | clamping | I_PP = 1 A, 8/20 µs | — | — | **8.0** | V |
| V_C | clamping | I_PP = 8 A, 8/20 µs | — | — | **12** | V |
| **C_J** | capacitance | V_R = 0, 1 MHz | — | **12** | 15 | pF |
| ESD | IEC 61000-4-2 contact | | — | — | ±30 | kV |
| ESD | IEC 61000-4-2 air | | — | — | ±30 | kV |

Bidirectional, 5 V working voltage, sits on the +5V rail near U9 (XC6206) Vin. **OK** — correct part for the rail it protects. 12 pF capacitance is borderline-high for a high-speed signal but acceptable on a power rail.

---

## 11. FMMT620TA (U3, LCSC C9032 — Diodes Inc. 80 V NPN low-saturation BJT, SOT-23)

**Datasheet read locally:** `_review/datasheets/FMMT620.pdf` (Diodes Inc. *FMMT620, doc DS33113 Rev 3-2, September 2012*, 7 pages).

### Specifications (Diodes Inc. DS33113 Rev 3-2, page 1-2)

| Parameter | Value |
|-----------|-------|
| BV_CEO | > 80 V |
| I_C continuous | 1.5 A |
| R_CE(sat) typical | 90 mΩ |
| Power dissipation | 625 mW |
| V_CE(sat) at I_C = 1 A, I_B = 50 mA | ~80 mV |
| h_FE @ I_C = 1 A | 100 — 250 (typ) |
| AEC-Q101 qualified | yes |

### Role on Twinspora

In the POWER IN block at (77.47, 234.95), alongside U4 (WSD4066DN33). Per v1's analysis (`_review/findings/v1_archive/01_schematic.md` NIT line 50): U3 acts as part of the **N-FET ideal-diode reverse-polarity scheme** — the BJT, biased from the DRV8316 charge-pump (VCP net), drives the gates of the two WSD4066 N-FETs to turn them on during normal-polarity operation, and is held off (or actively pulled down) when VCP is unavailable / during reverse polarity. The 80 V V_CEO survives 24 V + transient, and the high I_C / low V_CE(sat) is overkill but matches a generic high-side pre-driver role.

NIT — over-spec'd for this role; a MMBT3904 (V_CEO 40 V, I_C 200 mA, V_CE(sat) ~200 mV) would suffice except for the transient V_CEO rating. Acceptable.

---

## ESD coverage matrix (verified against schematic)

| Connector | Lines | ESD part | Channels protected | Verdict |
|-----------|-------|----------|---------------------|---------|
| J2 USB-C | VBUS, GND, D+, D-, CC1, CC2, SBU1, SBU2 | U6 SRV05-4A | D+, D-, CC1, CC2 (4 ch.) | **VBUS, SBU1, SBU2 unprotected** — see BLOCKER #2 |
| J7, J8 CAN (SH1.0 3-pin) | CAN_H, CAN_L, GND | U13 PESD2CAN + U12 ACT1210D CMC | CANH, CANL | OK |
| J11, J12 encoder (SH1.0 6-pin) | VCC, GND, MOSI, MISO, SCK, NSS | U17, U19 SRV05-4A | 4 SPI lines | VCC pin not protected — NIT |
| J5 (Qwiic? — verify pinout) | unclear, U10 covers 4 lines | U10 SRV05-4A | unknown | NIT — verify pin map |
| BK22 mezzanine (24 V, GND, etc) | +24V, GND | U5 SMF30CA | +24V transient | **CRITICAL — see BLOCKER #1, downgraded from v1 in light of corrected 40 V abs-max** |

---

## BLOCKERS — must address before fab

1. **SMF30CA TVS clamps above DRV8316C abs-max at full I_PP.** SMF30CA V_C = 48.4 V at I_PP = 4.1 A; DRV8316C V_VM abs max = 40 V (TI SLVSH07 § 7.1, p. 6). At sub-rated transients (≤ 2 A) the clamp is inside abs max but well above the 35 V operating max. **Fix:** swap U5 to `SMF24CA` (LCSC C19077515) — same SOD-123FL footprint, V_C = 38.9 V at full I_PP (under 40 V abs max). Or footprint-upgrade to SMA / SMAJ26CA (C19077544). See `_review/findings/07_smf30ca_deep_dive.md` for the full part-selection rationale (already correct).

2. **USB-C VBUS not ESD-protected.** SRV05-4A U6 covers 4 data lines (D+, D-, CC1, CC2). VBUS goes from J2 → D2 (1N4148WS, an OR-ing diode, not a TVS) → +5V. No polyfuse, no VBUS TVS. **Fix:** add a 5 V TVS (e.g. PESD5V0L2BT, SMAJ5.0CA) and a 0.5–1 A polyfuse on VBUS at J2.

3. **DRV8316C buck boots at 3.3 V; firmware must reprogram BUCK_SEL = 01b for 5 V.** TI SLVSH07 § 8.6.2.6, Table 8-23 (p. 67): Control Register 6 BUCK_SEL bits [2:1] reset value 0h = "Buck voltage is 3.3 V". On VBUS-absent power-up, the +5V rail will sit at ~2.6 V (BUCK 3.3 V – body-diode drop), the XC6206 LDO falls out of regulation, and the +3.3V rail drops below STM32 brown-out. **Mitigations:** (a) firmware reprograms the buck within milliseconds of POR; (b) document that bring-up requires USB-first; or (c) move U9 input from +5V to a wider-Vin LDO (e.g. AP2112-3.3, V_IN max 6 V, 250 mA, low dropout).

4. **CA-IF1044VD-Q1 VIO is driven by a GPIO, not a supply rail.** Per Chipanalog datasheet § 8.9 + § 9 Application Information, Figure 9-2 (p. 16, 18): VIO must be tied to the MCU's logic supply (3.3 V). The schematic instead drives `CAN_VIO` from STM32 PC4 (GPIO). This requires firmware to set PC4 high before any CAN traffic and exposes the GPIO to bus glitches via VIO. **Fix:** wire VIO directly to +3.3V; if remote-wake control is wanted, that is the STB pin (pin 8, currently tied to GND), not VIO.

---

## CRITICAL — should address before fab

- **Q1 OR-ing FET gate-discharge time** during VBUS removal. Gate is pulled down only via R11 = 10 kΩ to GND through R10 = 330 Ω; the resulting RC ~ 16 µs is fast enough that +5V should not brown out, but worth verifying with a scope on first prototypes.

- **Reverse-polarity protection topology** (Q3 + U4 + VCP gate-boost): functional only after VCP ramps up. During the brief "VM applied, no SPI yet" window, the body-diode of one WSD4066 conducts (V_SD ~0.75 V × peak I → up to 6 W transient at 8 A). Acceptable for short bring-up, document as a known startup constraint.

---

## NITS

- **MT6701 magnet placement**: confirm 0.5 – 2.0 mm air gap, diametrically magnetised Ø6 mm × 2.5 mm magnet centred on the QFN top face (Rev 1.8 § 6, p. 9). **No PCB copper-keepout dimension is specified by the datasheet** — needs PCB-review observation rather than a datasheet citation.
- **MT6701 VDD bulk cap**: 100 nF only; consider 1 µF if buck-rail noise propagates.
- **CAN STB tied to GND** (pin 8 + pin 9 EP joined to GND) — fixes the device in normal mode permanently. Acceptable; remote-wake feature is unavailable. NIT.
- **WSD4066DN33 V_GS(th) = 1 V (min)** — verify gate has a pull-down on the schematic block; ringing may inadvertently turn on the FET.
- **FMMT620TA over-specced**; smaller cheaper NPN would do.
- **SRV05-4A on encoder breakouts (U17, U19)**: VCC pin not ESD-protected — low-priority NIT.
- **U8 BOM label "H5VN10B"** vs. actual marking `H5VL10BC` — minor naming-only discrepancy, electrically the same part (same LCSC code C20615784).

---

## Datasheet sources used (all locally verified PDFs)

| Part | Doc ID / vendor file | Local path |
|------|---------------------|------------|
| DRV8316CR / CT | TI **SLVSH07** (Dec 2022) | `_review/datasheets/DRV8316C_TI.pdf` |
| MT6701 | MagnTek **Rev 1.8 (2022/12)** + **Rev 1.5 (2021/03)** | `_review/datasheets/MT6701_Rev1.8.pdf`, `MT6701_alt_MT6701QT-STD.pdf` |
| CA-IF1044VD-Q1 | Chipanalog **Version 1.05 (2023/09/01)** | `_review/datasheets/CA-IF1044VD-Q1.pdf` |
| ACT1210D-101-2P-TL00 | TDK **cmf_automotive_signal_act1210d_en.fm (2022/09/30)** | `_review/datasheets/ACT1210D_TDK.pdf` |
| PESD2CAN | Nexperia **Rev 2 (2012/09/27)** | `_review/datasheets/PESD2CAN.pdf` |
| SRV05-4 (cross-ref) | DOWO **Rev cross-ref** | `_review/datasheets/SRV05-4_DOWO_C2972082.pdf` |
| SMF30CA | Hongjiacheng **Rev 2.1** | `_review/datasheets/SMF30CA_C19077519.pdf` |
| XC6206P332MR | Torex **ETR0305_004b** | `_review/datasheets/XC6206P332MR_C5446.pdf` |
| AO3401A | AOS *AO3401A 30V P-Channel MOSFET* | `_review/datasheets/AO3401A.pdf` |
| WSD4066DN33 | Winsok **Rev 3.0 (Jan 2024)** | `_review/datasheets/WSD4066DN_C377861.pdf` |
| H5VL10BC | Zhuhai Hongjiacheng **Rev 2.0** | `_review/datasheets/H5VL10BC_C20615784.pdf` |
| FMMT620 | Diodes Inc. **DS33113 Rev 3-2 (Sept 2012)** | `_review/datasheets/FMMT620.pdf` |

---

## Corrections to v1 (`v1_archive/06_datasheet_others.md` and `v1_archive/01_schematic.md`)

1. **DRV8316C V_VM abs max** — v1's `06` and the SMF30CA writeup said **35 V**; correct value per TI SLVSH07 § 7.1 (p. 6) is **40 V**. The 35 V number is the *recommended operating maximum* (§ 7.3), not the absolute maximum. Also corrected in v2 of `07_smf30ca_deep_dive.md`.

2. **MT6701 MODE pin (settles the v1 disagreement)** — v1's `01_schematic.md` said MODE was **floating** and called this a BLOCKER (claimed it forces I²C mode incompatible with SPI). v1's `06_datasheet_others.md` said MODE was a no-connect with the internal 200 KΩ pull-up keeping it HIGH = I²C/SSI shared, and claimed SSI works.
   - **Both v1 documents had the schematic state wrong.** `magnetic_encoder.kicad_sch` actually **ties pin 14 (MODE) to +3.3V** via wires (153.67, 102.87) → (153.67, 83.82) → (140.97, 83.82) → +3.3V power symbol at (140.97, 77.47). This is electrically the same as the manufacturer's "floating + internal pull-up" default, and selects **I²C/SSI shared mode** for pins 6/7/8.
   - **The conclusion from v1's `06`** ("SSI works as intended") **is correct**.
   - **The BLOCKER claim from v1's `01`** ("MODE floating breaks SSI") **is wrong** — MODE in the I²C/SSI shared mode does not block SSI; the master selects SSI by pulling CSN low, exactly as the schematic does.

3. **U12 ACT1210D-101-2P-TL00 DNP status** — v1's `01_schematic.md` said the choke was "marked DNP / not populated". Wrong: schematic at line 38440 shows `(dnp no)`. The X markings inside the symbol body in `_review/s1_can.png` are the schematic-symbol drawing of the choke (showing two coupled inductors), not a do-not-populate marker.

4. **CA-IF1044VD-Q1 vendor** — v1 referenced TI's datasheet URL; the actual placed part (LCSC C5155979) is from **Chipanalog (上海川土微电子, Shanghai Chuantu)** with doc Version 1.05 (2023/09/01). It is a TI TCAN1044V-Q1 second-source, not a TI part. Pinout matches but ESD/transient numbers differ from TI's.

5. **SMF30CA blocker severity** — v1 called it an "actual fail" against the wrong 35 V abs max. Against the corrected 40 V abs max, the part is poor protection but not catastrophic for typical regen transients (≤ 2 A); it still fails at full I_PP 4.1 A. The deep-dive document (`07_smf30ca_deep_dive.md`) already corrected this; v1's `06` was based on the same wrong number.

6. **XC6206 V_IN abs-max** — v1 said 6 V (the *recommended operating max*); per Torex ETR0305_004b § Absolute Maximum Ratings (p. 3) the **abs max V_IN = 7.0 V**. Operating range 1.8 – 6.0 V.

7. **U8 part marking** — v1 calls the U8 ESD diode `H5VN10B`; LCSC C20615784 actual marking is **`H5VL10BC`**. Same device.

8. **WSD4066DN actual part name** — v1 calls it `WSD4066DN`; the Winsok Rev 3.0 datasheet gives the part as **`WSD4066DN33`** (per the datasheet header).
