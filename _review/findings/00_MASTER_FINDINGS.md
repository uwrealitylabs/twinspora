# Twin28xx — Pre-Fabrication Review (Master Findings, v2)

**Date:** 2026-05-05
**Board:** Twin28xx dual BLDC motor controller
**Specs:** 24 V nominal input, 3-5 A RMS / 8 A peak per motor phase, dual DRV8316C + dual MT6701 + STM32G473
**Stackup:** 4-layer FR4, 1.62 mm thick, no impedance control specified

This is the **v2 synthesis** after re-running every per-area agent with a strict "no paraphrasing — quote primary datasheets with section + page" mandate. The v1 versions are archived under `v1_archive/`. Per-area v2 details: `01_schematic.md`, `02_pcb_top.md`, `03_pcb_bottom.md`, `04_pcb_inner.md`, `05_datasheet_stm_drv.md`, `06_datasheet_others.md`, `07_smf30ca_deep_dive.md`.

The two factual errors that triggered the re-run (DRV8316C abs max 35→40 V; FOC P_CON formula 1.5× → 3×) are now fully propagated through the analysis. Several v1 blockers turned out to be false positives, several new ones surfaced, and the corrected current-capability calculation is significantly tighter than v1 reported.

---

## A. BLOCKERS — must fix before fabrication

### A1. PCB layout (mostly easy fixes)

| # | Issue | Where | Action |
|---|---|---|---|
| 1 | **Bulk electrolytic pads overhang top board edge** — C43 (109.0, 106.8) and C57 (123.7, 106.8) have **0.000 mm** clearance from VCC pad to top Edge.Cuts (y=100.8). Fab router will cut copper. | Top side, C43/C57 | Move both ~1 mm inward. |
| 2 | **GND via 0.190 mm from J9 PHB1 motor pin.** Drill registration tolerance can short motor phase to GND. | J9 vicinity | Move the via or shift J9. |
| 3 | **J5 / J1 GND pads 0.175-0.196 mm from bottom Edge.Cuts** (y=137.725). Four pads in violation. | J5, J1 | Shift connectors ~0.3 mm up. |
| 4 (NEW) | **U5 GND pad 0.165 mm from top Edge.Cuts.** Same family as #1-3, missed by v1. | U5 | Move ~0.3 mm inward. |
| 5 (NEW) | **9 stacked duplicate vias** — 8 around U15's exposed pad at the eight outer XY positions, plus 1 under U7 at (115.6, 132.6). These are duplicated `(via ...)` blocks in the .kicad_pcb. Will cause double-drill or fab reject. Source of 9 of 13 `holes_co_located` DRC errors. | U15 EP, U7 area | Single-edit fix — remove the duplicate via blocks. |
| 6 | **MT6701 encoders on the wrong side AND out of spec** — U16 (135.0, 120.03) and U18 (95.0, 120.03) are on F.Cu but motors mount on the back. Magnet→sensor distance: 1.617 mm FR4 + 0.700-0.800 mm package = **2.32-2.42 mm**. **MT6701 datasheet Rev 1.5 §5 page 8 specifies AG max = 2.0 mm** (typ 1.0, min 0.5). The encoder operates **0.32-0.42 mm OUT OF SPEC** — not "at the limit" as v1 claimed. | U16, U18 | Move both to B.Cu. |
| 7 | **Continuous GND pour fills all 4 layers under U16/U18.** Zone `In1.GND` (line 66621) covers F.Cu / In1.Cu / In2.Cu / B.Cu over the entire board outline; both encoder centers are inside the filled polygon on F.Cu, In1.Cu, AND B.Cu. Eddy currents will distort the rotating magnetic field. (Note: MagnTek's MT6701 datasheet does not specify a numeric keepout dimension — this is a magnetics-physics requirement, not a datasheet directive.) | All 4 layers, encoder areas | Add a circular copper keepout (radius ≥ magnet radius + ~1 mm guard) on every copper layer concentric with the magnet axis. |
| 8 | **Hard-switching PWM trace `/TIM8_CH2` runs 0.617 mm from U18's die.** v1 had this less precise and named the wrong worst signal. Actual measured distances from U18 (95, 120): /TIM8_CH2 = 0.617 mm (clipping the courtyard SW corner!), /TIM8_CH3 = 1.819 mm, /TIM8_CH3N = 2.028 mm, /SPI1_MISO = 2.621 mm (just outside ±2 mm — v1 was wrong about this one). | B.Cu near U18 | Reroute these signals away from the encoder. With fix #6 (move to B.Cu) and fix #7 (keepout), this becomes mandatory. |
| 9 | **No motor-shaft cutouts in Edge.Cuts.** Outline is a single rounded rectangle (8 elements lines 45476-45558). | Edge.Cuts | Add cutouts or confirm shafts don't protrude through PCB. |

### A2. Schematic / electrical

| # | Issue | Where | Action |
|---|---|---|---|
| 10 | **CAN-FD termination jumper logic mis-designed.** Default config (R21 DNP, J6 DNP, R27/R28 populated) leaves bus with NO termination. With R21 populated, R27/R28 end up between CAN_H and the C30/GND center as a shorted asymmetric load — *not* a 60+60 Ω split termination. Only "J6 alone" gives a valid termination. | CAN bus around U11/J5 | Re-think the jumper logic. The schematic should either default-populate a clean split termination, OR provide a clear single-jumper toggle for end-of-bus vs middle-of-bus. |
| 11 | **DRV8316C nFAULT pull-up is an LED + 330 Ω in series with +3.3V — not a real pull-up.** TI SLVSH07 §6 p.5 and §8.3 Table 8-1 p.19 require nFAULT > 2.2 V at power-up to avoid **test-mode lockup**. During the +3.3 V rail's bring-up the LED forward-drop and 330 Ω impedance can keep nFAULT below 2.2 V for several ms. | DRV8316 nFAULT net | Add a real ~10 kΩ pull-up from nFAULT to +3.3 V; keep the LED in parallel for fault indication. |
| 12 | **DRV8316C BUCK_OUT defaults to 3.3 V at boot** (BUCK_SEL reset = 00b per TI SLVSH07 §8.6.2.6 Table 8-23 p.67). On first power-up with no firmware, the DRV's buck delivers 3.3 V → P-FET-OR'd +5V rail sits at ~3.0 V → XC6206 LDO falls into dropout → +3.3 V rail at ~2.6 V → MT6701 below its 3.3 V minimum (§5 p.7). Cold-start chicken-and-egg. | DRV8316 buck control | Hard-strap BUCK_SEL high so the DRV comes up at 5 V regardless of firmware. (Or verify USB will be present at every cold-start, which is implausible.) |
| 13 | **CA-IF1044VD-Q1 VIO driven by STM32 GPIO PC4** instead of a permanent supply rail. Chipanalog datasheet §9 Fig 9-2 requires VIO tied to MCU supply. CAN dies with the MCU — boot-time CAN, hung-MCU CAN, and bootloader-over-CAN all impossible. | U11 VIO pin | Tie VIO directly to +3.3 V. |
| 14 | **CAN bus ships unprotected: ACT1210D CMC populates fine (was a v1 false alarm — the X marks were symbol coupling glyphs, not DNP), but the 120 Ω termination jumper still depends on the broken logic in #10.** Plus PESD2CAN ESD is OK. | CAN bus | Subsumed by #10 fix. |
| 15 | **QWIIC I²C bus has no working pull-ups.** R15/R16 = 120 Ω in *series* with SDA/SCL (CAN-style termination values miscoded onto an I²C bus). Only pull-up R18 is gated by DNP jumper J4 and is on SDA only — SCL has no pull-up at all. | Top sheet, J5 area | Replace 120 Ω series Rs with 0 Ω; add 4.7-10 kΩ pull-ups on both SDA and SCL to +3.3 V; populate J4 or remove it. |
| 16 | **SMF30CA TVS clamps 8 V over DRV8316C abs max.** V_C = 48.4 V at I_PP = 4.1 A (Hongjiacheng Rev 2.1 p.2). DRV8316C abs max VM = 40 V (TI SLVSH07 §7.1 p.6). At sub-rated transients (≤ 2 A) it stays inside abs max but well over the 35 V operating ceiling, tripping the DRV's VM_OVP. | U5 | Same SOD-123FL footprint: swap to **SMF24CA (LCSC C19077515)** — V_C = 38.9 V at I_PP, under abs max. Better: footprint to DO-214AC and use SMAJ26CA. See `07_smf30ca_deep_dive.md`. |

---

## B. CRITICAL — should fix (functional risk, not a fab show-stopper)

### B1. PCB layout

- **DRV8316 ceramic decoupling caps 6-8 mm from VM/CPH/CPL pins.** v1 quoted ~3.4 mm but that was distance to EP center. Actual distance to the relevant power pins is 6-8 mm; TI SLVSH07 §11.2 example shows ~2 mm. At 6-8 mm the bypass loop inductance defeats the 100 nF / 47 nF caps at switching transitions.
- **BK22 (U1, U2) power-input vias are sparsely stitched** — only 0-1 GND vias within 3 mm of each connector vs. 18 unique GND vias under each DRV8316 EP. (Updated count: TI SLVSH07 §11.1 has no specific count rule, but §11.2 shows a 4×4 = 16-via reference; this board has 18 — *exceeds* the example. Prior "22" was inflated by counting U15's duplicated stacked vias from blocker #5.) The deficiency is at the BK22, not at the EP — high-current return into the bulk caps takes too long a path.
- **In2.Cu is a split power plane WITH signals routed on it** (verified: zone fills for VCC_IN2 line 82846, VBAT line 83185, +3.3V_BCC line 83937; plus 142 routed segments across 17 nets). Any B.Cu trace crossing a power-rail boundary breaks return path.
  - **CAN-FD pair fragmented**: CAN_H = 62 segments / 123.9 mm, CAN_L = 42 segments / 112.4 mm — **11.5 mm length mismatch** alone, plus return-path discontinuity at every layer transition.
  - **Current-sense `/SOC2` jumps F.Cu ↔ In2.Cu** through the noisy split-plane region. (v1 said all four `/SOA2 /SOB2 /SOC2 /SOC1` did — actually only `/SOC2`. v2 corrected.)
- **12 starved-thermal connections** (single-spoke instead of dual): STM32 U7 pin 63, X1 crystal pins 2 & 4 (clock-stability concern), J5 GND, decoupling caps C8 / C14 / C23 / C59 / C60. Right-click → properties → Spoke style: Default override.
- **M3 mounting-hole NPTH conflict** (H1 / H4 / H7 / H10 SMD standoffs stacked on M3 PTH pads) — 18 hole-clearance + 33 hole-to-hole DRC errors (count updated for KiCad 10). Either move the stitching vias outside the standoff keepout or get explicit DRC waiver from fab.
- **18 courtyard overlaps** in dense central area — pick-and-place is OK, rework headroom is gone.
- **25 F.Cu footprints have their Reference text on B.Silkscreen mirrored** (v1 said "26+", actual count is 25). Bottom silk will print labels for parts that don't exist on the back.

### B2. Schematic

- **Thermal envelope is the binding limit for motor current.** Re-derived per TI SLVSH07 §11.3.1 Table 11-1 (FOC: P_CON = 3 × I_RMS² × R_DS(on)) and §7.4 (θ_JA = 25.7 °C/W). Result table:
  - **T_A = 25 °C, T_J = 125 °C, max slew**: ~2.7 A_RMS continuous
  - **T_A = 85 °C, T_J = 125 °C, max slew**: ~1.3 A_RMS continuous
  - **T_A = 25 °C, T_J = 140 °C, max slew**: ~3.1 A_RMS continuous
  - **T_A = 85 °C, T_J = 140 °C, max slew**: ~1.6 A_RMS continuous
  - With default slew rate (50 V/µs) instead of max, derate further by ~30 %.
- The user's 3-5 A_RMS target is **only feasible at low ambient (≤ 40 °C) with max slew rate and tight T_J target**. 8 A peak transient is fine. TI's own headline ("<80 W motors at 12-24 V") backs ~2-3 A continuous — consistent with this calc, not with v1's 3-5 A claim.
- **HSE crystal load caps over-loaded.** ST DS12288 §5.3.10 p.123 explicitly specifies stray Cs = 10 pF (v1 used 3-5 pF). With C11/C18 = 30 pF: CL_eff = (30·30)/60 + 10 = 25 pF. X322512MSB4SI datasheet load = 20 pF. **Optimal cap value = 20 pF each.** Current values cause slow startup and small frequency offset.
- **DRV8316C nSLEEP is on the 100 kΩ + Zener path and is NOT routed to the MCU at all** (NEW finding from v2 schematic agent — v1 had nFAULT and nSLEEP wrongly bundled). Firmware has no software control over DRV sleep; the DRV always sees nSLEEP high (driven from VCC through the divider). Power-management implication: cannot put DRV into 1.5 µA sleep mode for low-power operation.
- **DRV8316C VREF/ILIM (pin 37) connection unverified.** TI SLVSH07 Table 6-1 p.5: in default PWM Mode 1 (PWM_MODE reset = 00b = 6× PWM), pin 37 is the CSA reference and must have 0.1 µF cap to AGND; if floating, current sensing breaks. Needs visual check in `motor_driver.kicad_sch`.
- **STM32 VDDA not isolated from digital +3.3V.** ST AN4488 §3.3.2 p.14 says ferrite "can be" used (recommendation, not requirement). The 2× (100 nF + 1 µF) decoupling pairs (C25-C28) **do exist** (v1 missed this). Performance impact: 1-2 ENOB ADC degradation that affects current-sense reads. **Demoted from CRITICAL in v1 to "should consider" — adding a ferrite is cheap.**

### B3. ERC / DRC summary

- **132 ERC violations: 17 errors + 115 warnings.** Of the 17 errors:
  - 6× `label_dangling` on top sheet for `/PHA1`, `/PHB1`, `/PHC1`, `/PHA2`, `/PHB2`, `/PHC2`. **NOT broken motor connections** — Conn_01x03 J9/J10 motor connectors live inside `motor_driver.kicad_sch` (line 5985), so motor phases route correctly via the subsheet. The top-level labels are debug stubs to be deleted to silence ERC. (v1 agent 5 and v2 agent 5 both called this a BLOCKER. Wrong both times.)
  - 2× `power_pin_not_driven`: U9 (XC6206) Vin and H1 pin 1. Both are KiCad library artifacts — Q1 P-FET drain symbol-pin type is "passive" (not "power-output"), so KiCad doesn't see the +5V net as driven; H1 is a mounting-hole symbol with a bogus power pin. Real circuit is fine — agent 6 v2 traced wires explicitly (twin28xx.kicad_sch lines 14175/14425/33958) and confirmed +5V drives U9 V_in.
  - 9× `pin_to_pin` errors and 70× `pin_to_pin` warnings — many are symbol-library cosmetic; some real (diode-bridge symbol artifacts).
- **719 DRC violations** (down from 758 after your earlier fixes). Of those: ~509 cosmetic silk (199 silk_over_copper, 192 text_height, 118 silk_overlap), 46 lib_footprint_mismatch, 16 padstack_invalid, plus the electrical/mechanical issues called out in A1.

---

## C. NITS — improvements / cosmetic

- **VDDA ferrite missing** (demoted from v1 CRITICAL — see B2 note). AN4488 frames it as optional; low-priority improvement.
- **6 dangling top-level motor-phase labels** (debug stubs — delete to silence ERC).
- **2 zombie tracks** `/SPI2_MISO` and `/BOOT` (track_dangling).
- **Test point `/VCP` unconnected.**
- **DRVOFF default state**: confirm it boots in a safe (no-PWM) state before MCU comes up.
- **USB CC pull-down caps C1, C2 (47 pF) are DNP** — fine for stock USB-C device-mode. (The 49.9 Ω resistors that v1 thought were USB series resistors are actually on the SOx current-sense ADC filter path — v2 corrected this, no USB external Rs are needed since STM32G4 has internal D+ pull-up.)
- **ADC channel naming**: v1 said off-by-one. v2 verified **correct** against DS12288 Rev 1 Table 12. Removed.
- **VCC ampacity** for 8 A peak: v1 claimed it from IPC-2152, v2 couldn't verify against a primary-source IPC PDF. Probably fine given the pour geometry, but the master limit is the DRV8316 thermal envelope (B2) at ~1.5 A_RMS at 85 °C ambient — well below the trace ampacity question.
- DRV8316 datasheet URL in symbol property — wrong link.

---

## D. Analytical sims — answers to your questions (corrected)

### D1. "How much current can the board safely handle?"

**Verified directly from TI SLVSH07 datasheet.**

**Answer: ~1.3-1.6 A_RMS continuous per phase at 85 °C ambient. ~2.7-3.1 A_RMS at 25 °C ambient. 8 A peak transient is fine.** The user's 3-5 A_RMS target is **not safely achievable continuous on the standard 4-layer board at 85 °C ambient** without active cooling. At 25 °C ambient with max slew rate, ~3 A continuous is feasible.

Verified inputs:
- V_VM operating: 4.5/24/35 V min/nom/max (sec 7.3 p.6); abs max 40 V (sec 7.1 p.6).
- R_DS(on) HS+LS: typ 95 mΩ / max 120 mΩ at T_A=25 °C; typ 140 mΩ / max 185 mΩ at T_J=150 °C (sec 7.5 p.11).
- θ_JA: **25.7 °C/W** (sec 7.4 p.7, JEDEC 4-layer reference).
- P_CON (FOC) = **3 × I_RMS² × R_DS(on)** (sec 11.3.1 Table 11-1 p.85).
- P_SW = 3 × I_RMS × V_PK × t_rise/fall × f_PWM.

The v1 calc had two compounding errors: P_CON formula off by 2× (used 1.5×, should be 3×) and θ_JA off by 28% (used 33, should be 25.7 — but 25.7 is *better*, partially compensating). Net: v1 was ~50% optimistic. Corrected numbers are conservative.

### D2. IR-drop on power rails

VCC pour ampacity is not the binding limit; the DRV8316 thermal envelope is. At ~1.3-2 A_RMS the IR drop on VCC is negligible (< 50 mV).

### D3. Signal-integrity for fast signals

- **USB FS (12 Mbps)**: routes over solid In1.GND, no impedance issue at this rate. Good.
- **CAN-FD (5 Mbps)**: layer-fragmented diff pair (62 vs 42 segments, 11.5 mm length mismatch) — needs reroute as a clean diff pair on F.Cu over In1.GND. Key concern.
- **SPI to encoders**: short, low-rate. No SI concern.
- **HSE 12 MHz crystal**: load caps over-loaded by ~5 pF (D2/B2 above). Slow startup, small freq offset. Cosmetic-functional.

---

## E. Positive findings (sanity confirmations)

- **In1.Cu = clean solid GND plane** — verified by parser, zero routed segments. Textbook L2.
- **In2.Cu = split power + signals** — known constraint; B.Cu signals crossing splits is the SI risk.
- **18 unique GND vias under each DRV8316 EP** — exceeds TI's reference 16-via array (sec 11.2 p.84). Good thermal coupling.
- **MT6701 is correctly wired for I²C/SSI mode** — MODE pin hard-tied to +3.3V (verified `magnetic_encoder.kicad_sch` lines 2273/2193/2333/3129). Per Rev 1.8 §1.2 p.4 the chip supports both I²C and SSI on the same pins; master selects SSI by pulling NSS low. Both v1 agents had this wrong.
- **CAN choke U12 (ACT1210D-101) is populated**, not DNP. v1 false alarm — the X marks in the rendered schematic were the symbol's coupling glyph, not DNP markers.
- **DRV8316C charge-pump cap (C32 / C46 = 47 nF)** is correct for the C-variant. Confirmed.
- **DRV8316C VM bulk capacitance** (660 µF total per driver: 330 µF SMD + 330 µF THT) is generous.
- **BUCK power-OR architecture** (DRV buck OR'd with USB VBUS via Q1 P-FET) is clever and works in principle. Cold-start sequencing (#12) is the only catch.
- **Edge.Cuts is closed and clean** (pending the motor-shaft cutout question, #9).
- **SWD debug header / test points** confirmed accessible.
- **VDDA decoupling pairs (C25-C28) exist** (v1 missed this).

---

## F. Items I could NOT verify (open questions)

- DRV8316C VREF / ILIM (pin 37) connection — schematic-side trace not completed by agents. Visual check needed in `motor_driver.kicad_sch`. If floating in 6× PWM mode, current sensing breaks → FOC unusable. Cheap to verify.
- IPC-2152 8 A ampacity number — no IPC PDF available locally; agents cited the standard qualitatively only. Master thermal limit (D1) is binding anyway.
- ST DS12288 Rev 1 directly from ST — agents used a Farnell mirror PDF (same DS12288 content, doc-ID-verified). Fine in practice.
- Chipanalog CA-IF1044VD-Q1 full datasheet — LCSC anti-leech blocked; agent used TI TCAN1044V-Q1 SLLSF17D as functional twin. Some Chipanalog clones have NC on pin 5 instead of VIO; if your specific part is one of those, blocker #13 is moot. Verify the actual part-page on LCSC.
- SRV05-4A exact vendor — no LCSC code in BOM. Agent used DOWO datasheet as cross-reference. Check the BOM line.
- X322512MSB4SI Cm/C0 — used typical values for the frequency-pulling estimate (D2/B2). Order-of-magnitude correct.
- MT6701 PCB copper-keepout dimension — datasheet has no PCB-layout section. Sized #7 by magnet geometry (radius + ~1 mm guard).

---

## G. What I'd actually do, in order

1. **Fix the four PCB-edge-clearance issues** (#1-4): 5-minute moves. Fab will reject as drawn.
2. **Remove the 9 stacked duplicate vias** (#5): single edit kills 9 DRC errors.
3. **Move U16/U18 encoders to B.Cu** (#6) and **add magnet-axis copper keepouts on every layer** (#7). Reroute B.Cu signals away from encoder die (#8). This is the big layout change.
4. **Add motor-shaft cutouts to Edge.Cuts** (#9).
5. **Replace SMF30CA → SMF24CA** (#16) — same SOD-123FL footprint, drop-in.
6. **Hard-strap DRV8316 BUCK_SEL high** (#12) so 5 V rail comes up at 5 V on power-on.
7. **Add real 10 kΩ nFAULT pull-up** to +3.3V (#11), keep the LED.
8. **Re-do CAN termination jumper logic** (#10); **wire CAN_VIO to +3.3V** (#13); fix QWIIC pull-ups (#15).
9. **Verify DRV VREF/ILIM pin 37 cap exists and is 100 nF to AGND** (B2 / F).
10. **Pull DRV nSLEEP onto an MCU GPIO** if you ever want sleep-mode power saving.
11. Layout cleanups: re-pour around BK22 with denser GND stitching (B1); fix 12 starved-thermal connections; resolve M3 standoff conflict; reroute CAN-FD as clean diff pair on F.Cu over In1.GND.
12. Cosmetic ERC pass: delete dangling motor-phase labels, fix mirrored-on-back silk references, etc.
13. Optional: change C11/C18 to 20 pF for cleaner crystal startup; add VDDA ferrite if ADC noise floor matters.

After items 1-10 the board should be ready for first articles.
