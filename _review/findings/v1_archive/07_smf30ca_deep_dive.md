# SMF30CA vs SMF24CA — TVS deep dive for Twin28xx 24 V input

**Goal:** decide whether to keep U5 = SMF30CA (LCSC C19077519) or swap to SMF24CA, and what the right choice actually is given the DRV8316C's 35 V VM absolute maximum.

Datasheets read locally:
- `_review/datasheets/SMF30CA_C19077519.pdf` (Hongjiacheng / R+O, 5 pages, the actual placed part)
- `_review/datasheets/SMF24CA_C123811.pdf` (MDD/Microdiode SMF5.0CA-440CA series, 4 pages)
- `_review/datasheets/SMF30CA_C284106.pdf` (DOWO — same SMF series, different vendor, for cross-check)

Both are SOD-123FL, bidirectional ("CA" suffix), 200 W peak pulse power, JEDEC SMF series. Electrical specs are tightly standardized across vendors.

---

## 1. Datasheet-extracted electrical specs

| Parameter | SMF30CA | SMF24CA | Notes |
|---|---|---|---|
| Package | SOD-123FL | SOD-123FL | Same footprint — drop-in swap. |
| Polarity | Bidirectional | Bidirectional | "CA" = bidirectional. |
| **V_RWM** (working peak reverse voltage / standoff) | **30 V** | **24 V** | Voltage at which it must NOT conduct (≤ 1 µA leakage). |
| **V_BR min** @ I_T = 1 mA | **33.3 V** | **26.7 V** | Where breakdown actually starts at the 1 mA test current. |
| **V_BR max** @ I_T = 1 mA | **36.8 V** | **29.5 V** | Upper-tolerance breakdown (5 % tol "A" suffix). |
| **V_C** (max clamping @ I_PP, 10/1000 µs) | **48.4 V** | **38.9 V** | The actual voltage the rail sits at during a rated transient. |
| **I_PP** (peak pulse current, 10/1000 µs) | **4.1 A** | **5.1 A** | Rated transient current the diode survives without damage. |
| Clamp factor V_C / V_BR_min | 1.45 | 1.46 | Same family, same factor. |
| **I_R** (leakage @ V_RWM) | **1 µA** | **1 µA** | Below the leakage knee. |
| P_PPM (peak power, 10/1000 µs) | 200 W | 200 W | 48.4 V × 4.1 A ≈ 198 W, 38.9 V × 5.1 A ≈ 198 W — checks out. |
| I_FSM (forward surge, 8.3 ms half-sine) | 30 A | 20 A | (Hongjiacheng vs MDD vendor difference; both bidirectional clamp similarly.) |
| Junction capacitance @ V=0 | ~50-150 pF (graph) | ~50-150 pF (graph) | Higher than ESD-only diodes; not a concern on a 24 V power rail. |
| Steady-state P_M(AV) @ T_L = 75 °C | 0.4 W | 1.0 W | Vendor-dependent thermal numbers. |
| θ_JA (typical) | 220 °C/W (R+O) | 180 °C/W (MDD) | Both poor, as expected for SOD-123FL — TVS is for *transient* energy, not continuous. |
| T_J max | 150 °C | 150 °C | Same. |

Both behave identically over the operating range; the only meaningful differences are the four numbers in **bold**.

---

## 2. Twin28xx operating constraint

- **V_nominal** at the BK22 mezzanine: 24 V (per your spec)
- **Supply tolerance**, realistic worst-case: 24 V ± 10 % → up to **26.4 V** continuous
- **Motor regen overshoot**: BLDC braking back-EMF can push the rail well above nominal. With 1320 µF of bulk on the board (2× 330 µF SMD + 2× 330 µF THT) the rail is stiff, but a hard brake from full speed on an open bus can still spike multiple volts.
- **DRV8316C VM**:
  - Operating range (datasheet table 6.3): **8 V to 40 V**
  - **Recommended operating range: 4.5 V to 35 V** (TI product page).
- **Absolute maximum: 40 V** (TI product page; do-not-exceed for transients/sustained — above 40 V is damage territory).
- VM_OVP self-shutdown trips at typ. ~37 V — internal protection that disables the FETs while still inside abs-max. This is the *operating* upper guardrail, not a *protection* threshold.
- Design constraints, in order of severity:
  1. **Hard ceiling: V_M ≤ 40 V** — exceeding this damages the silicon.
  2. **Operating ceiling: V_M ≤ 35 V** — between 35 V and 40 V the device will trigger its own OVP shutdown; not damaging, but motor control stops until VM falls back. Brief transient excursions are acceptable as long as the OVP can recover and you don't camp there.

This is what we're trying to protect.

---

## 3. Verdict on SMF30CA (the part you placed)

| Behaviour zone | Rail voltage | What SMF30CA does | DRV8316C state |
|---|---|---|---|
| Normal | 24 V | Off (≤ 1 µA). Good. | In operating range. |
| 10 % overvoltage | 26.4 V | Off (well below V_RWM = 30 V). | In operating range. |
| Mild transient / regen | 30-33 V | Still off — V_BR_min is 33.3 V. **DRV8316 is on its own up to 33 V before the TVS even starts working.** | OVP may trip near 37 V; auto-recovers after transient. |
| Rated transient | up to **48.4 V at 4.1 A** | **Clamp voltage is 48.4 V — DRV8316 sees 48 V during a clamped event.** | **8.4 V over abs max (40 V) — silicon damage region.** |
| Lower-current transient (1-3 A) | ~37-44 V | Operating in V_BR knee region | Above operating max but inside abs max — OVP trips, motor control stops briefly. |

**SMF30CA fails to protect at full rated transient.** At I_PP=4.1 A the clamp voltage exceeds DRV8316C's 40 V abs max by 8 V. At lower-magnitude transients (~1-3 A) it's inside abs max but well above operating max, so the DRV's OVP trips and motor control briefly halts.

It's not as catastrophic as I first wrote (the abs max is 40 V, not 35 V), but the SMF30CA is still the wrong part for this rail — there's effectively no protection until 33 V, and the worst-case clamp violates abs max.

---

## 4. Verdict on SMF24CA (originally proposed replacement)

| Behaviour zone | Rail voltage | What SMF24CA does | DRV8316C state |
|---|---|---|---|
| Normal | 24 V | At the leakage knee. **V_RWM = V_nom — no supply-variation margin.** | In operating range. |
| 10 % overvoltage / ripple | 26.4 V | **At/just over V_BR_min = 26.7 V.** Conducts a small but non-trivial current — milliamps, with continuous heating. | In operating range. |
| Rated transient | up to **38.9 V at 5.1 A** | Clamps to 38.9 V — **inside the 40 V abs max** ✓. Above the 35 V operating max, OVP trips briefly. | Inside abs max — silicon safe. |
| Sub-rated transient (1-3 A) | ~29-34 V | Operating inside abs max and roughly at operating-max boundary. | OVP may flicker near 35 V; otherwise within spec. |

**Re-evaluated: SMF24CA actually does keep the DRV inside its 40 V abs max** — even at full I_PP it clamps to 38.9 V. My original "blocker" call was based on a wrong abs-max number; against the true 40 V it does the job.

**The remaining problem with SMF24CA is the leakage knee at nominal supply**, not the clamp voltage:
- V_RWM = 24 V on a 24 V rail means the diode is right at its leakage corner during normal operation.
- Any positive deviation from nominal (10 % supply tolerance, regen lift, ripple, brief surges) puts the diode into the early-breakdown region where it draws milliamps continuously.
- That's not damage — it's just inefficient and produces a tiny amount of heat. On a regulated, well-filtered 24 V rail (like yours, with 1320 µF of bulk capacitance) this is acceptable. On an unregulated battery / wall-wart input it would be a real problem.

**Net: SMF24CA is a legitimate fix on this board's regulated 24 V rail. The earlier "SMF24CA is worse than SMF30CA" was overstated.** It is a step better than SMF30CA — clamps under abs max — though not quite as clean as a higher-V_RWM SMA/SMB part.

---

## 5. The actual fix — JLCPCB-orderable candidates

All candidates below were verified against your JLCPCB parts library snapshot (`D:\JLC_inf_scroll\jlcpcb_com-parts-2026-05-05-07-30-22.html`). **All are "Extended" parts**, same tier as the SMF30CA you already specified — so no change in JLC's per-line setup-fee economics.

Effective clamp at a *realistic* motor-regen transient is what matters, not the V_C@I_PP datasheet headline. Approximating with the linear dynamic-resistance model V(I) ≈ V_BR_min + (V_C − V_BR_min) × (I / I_PP), I get:

| LCSC | Part | Pkg | V_RWM | V_BR_min | V_BR_max | V_C @ I_PP | I_PP | Power | V at 1 A | V at 3 A | V at 5 A | Stock | Price | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **C19077519** ⬅ | **SMF30CA** *(current)* | SOD-123FL | 30 V | 33.3 V | 36.8 V | 48.4 V | 4.1 A | 200 W | 36.9 V | 44.4 V | over | 151,814 | $0.0152 | ❌ V_C exceeds 40 V abs-max at >2 A. No protection until 33 V. |
| ✅ C19077515 | SMF24CA | SOD-123FL | 24 V | 26.7 V | 29.5 V | **38.9 V** | 5.1 A | 200 W | 29.1 V | 33.9 V | 38.7 V | **1,459,163** | $0.0152 | ✅ **Stays under 40 V abs max even at full I_PP.** Caveat: V_RWM = supply means leakage knee at nominal. Acceptable on regulated 24 V rail. |
| ✅ C19077516 | SMF26CA | SOD-123FL | 26 V | 28.9 V | 31.9 V | **42.1 V** | 4.8 A | 200 W | 31.6 V | 37.1 V | 42.6 V | 3,933 | $0.0153 | ⚠️ Crosses 40 V abs max at ~4 A. Inside abs max for typical transients (≤3 A). Trades clamp ceiling for 2 V supply-variation margin. |
| C19077517 | SMF28CA | SOD-123FL | 28 V | 31.1 V | 34.4 V | 45.4 V | 4.4 A | 200 W | 34.4 V | 41.1 V | over | 345,625 | $0.0152 | ❌ V_C exceeds 40 V at >2 A. Worse than SMF26CA. |
| ✅ **C19077542** | **SMAJ24CA** | DO-214AC (SMA) | 24 V | 26.7 V | 29.5 V | 38.9 V | 10.3 A | 400 W | 27.9 V | 30.3 V | 32.6 V | 98,854 | $0.0203 | ✅ Clamps comfortably under both ceilings at all realistic transients. Same V_RWM-at-knee caveat as SMF24CA. |
| ⭐ **C19077544** | **SMAJ26CA** | DO-214AC (SMA) | **26 V** | **28.9 V** | 31.9 V | 42.1 V | 9.5 A | 400 W | **30.3 V** | **33.1 V** | **35.8 V** | 27,895 | $0.0170 | ✅ **Sweet spot.** 2 V margin over supply, 4-7 V under 40 V abs max at realistic transients. |
| C19077546 | SMAJ28CA | DO-214AC (SMA) | 28 V | 31.1 V | 34.4 V | 45.4 V | 8.8 A | 400 W | 32.7 V | 36.0 V | 39.2 V | 36,339 | $0.0195 | ⚠️ Inside abs max but tight. Pick only if real worst-case continuous can hit 27 V. |
| C8834 | SMBJ24CA | DO-214AA (SMB) | 24 V | 26.7 V | 30.7 V | 38.9 V | 15.2 A | 600 W | 27.5 V | 29.1 V | 30.7 V | 923 | $0.0419 | ✅ V_RWM-at-knee caveat; otherwise excellent clamp. Low stock. |
| ⭐ **C8835** | **SMBJ26CA** | DO-214AA (SMB) | **26 V** | **28.9 V** | 33.2 V | 42.1 V | **14.2 A** | 600 W | **29.8 V** | **31.7 V** | **33.5 V** | 3,805 | $0.0390 | ✅ **Tightest clamp with 2 V supply margin.** Bigger footprint than SMA, real PCB-area cost. |
| C8837 | SMBJ30CA | DO-214AA (SMB) | 30 V | 33.3 V | 38.3 V | 48.4 V | 12.4 A | 600 W | 34.5 V | 36.9 V | 39.4 V | **2** | $0.0441 | ❌ same V_C as SMF30CA — too high; also nearly out of stock. |
| C19077605 | SMCJ26CA | SMC (DO-214AB) | 26 V | 28.9 V | 31.9 V | 42.1 V | 35.7 A | 1500 W | 29.3 V | 30.0 V | 30.7 V | 70,186 | (?) | ✅ Tightest clamp of all. Biggest footprint. Probably overkill. |
| C19077606 | SMCJ28CA | SMC (DO-214AB) | 28 V | 31.1 V | 34.4 V | 45.4 V | 33.1 A | 1500 W | 31.5 V | 32.4 V | 33.2 V | 5,203 | (?) | ✅ similar; one step higher V_RWM. |

(`V at I_pp` columns are linear-model estimates of the actual clamp voltage during a transient of that magnitude. Real curves are slightly sub-linear — actual clamps will be a tad lower. Numbers in **bold** are the parts I'd recommend; ⭐ marks them.)

### Pick by constraint

1. **Best electrical fit, minimum PCB rework**: **SMAJ26CA** (LCSC C19077544). DO-214AC (SMA) — replaces SOD-123FL but still small. Clamps ~33 V at a 3 A regen transient. $0.017, 27 k in stock. Footprint change: SMA is 5.0 × 2.6 mm vs SOD-123FL's 3.7 × 1.8 mm — fits in roughly the same area as a 1206 cap.
2. **Highest protection margin (more board space)**: **SMBJ26CA** (LCSC C8835). DO-214AA (SMB), 600 W. Clamps ~32 V at 3 A regen transient. $0.039, 3.8 k in stock. SMB is 5.4 × 4.2 mm — needs more area than SMA but still small.
3. **If you must keep SOD-123FL footprint**: pick **SMF24CA** (LCSC C19077515) and accept the trade-offs:
   - Clamps to ~34 V at 3 A — works, but no margin.
   - V_RWM = V_nominal → conducts at any 26 V+ supply lift, expect mild leakage heating during supply ripple. Acceptable on a regulated 24 V supply, marginal on a battery / unregulated input.
   - Stock is huge (1.4 M pieces).
   - This is *better than today's SMF30CA* but is still a band-aid. **Use only if SMA pad change is impossible.**
4. **Belt-and-suspenders**: SMAJ26CA *plus* a small ~4.7 µH series inductor before the TVS will reduce dv/dt and bring the effective clamp 1-2 V lower during fast transients. Optional.

### Footprint-change effort (PCB-side)

The current footprint is `Diode_UWRL:SOD-123FL_L2.7-W1.8-LS3.8-BI` at U5. Swapping to SMA or SMB needs:
- New footprint assignment in the schematic symbol (just edit U5's footprint property).
- Pad relocation on the board — both SMA (`DO-214AC`) and SMB (`DO-214AA`) are widely available in `Diode_SMD` and KiCad's standard libs.
- Re-pour the VCC plane around the larger pad.
- Re-DRC.

Total time: ~10 minutes per part choice. No re-routing of any other net.

---

## 6. Bottom line (revised against true 40 V abs max)

- **SMF30CA still doesn't protect well**: clamps to 48 V at I_PP (8 V over 40 V abs max), and offers no protection until the rail hits 33 V. At realistic 1-3 A transients it's inside abs max but well over the 35 V operating ceiling — DRV's OVP trips and motor control briefly halts.
- **SMF24CA in the same SOD-123FL footprint is actually fine for this board.** Worst-case clamp 38.9 V (under 40 V abs max), and your bulk capacitance handles the supply-variation leakage concern. **It is a legitimate same-footprint drop-in fix** — the earlier "blocker / worse than SMF30CA" claim was based on my wrong 35 V abs-max number.
- **For tighter protection with a small footprint change**: SMAJ26CA (C19077544) — DO-214AC, $0.017, 28 k in stock, clamps in the low 30 s V at typical regen, 2 V margin over 24 V nominal supply.
- **For maximum protection margin with a bigger footprint**: SMBJ26CA (C8835) — DO-214AA, $0.039.
- All "Extended" tier on JLC, same as your current SMF30CA, no change in setup fees.

### What I'd actually do
- **If you want a single-line BOM change with no PCB rework**: swap U5 to **SMF24CA (LCSC C19077515)**. Same SOD-123FL pads, same $0.0152, 1.46 M in stock. Worst-case clamp 38.9 V. ✓
- **If you're already touching the PCB for the other blockers in the master findings**: change U5's footprint to DO-214AC (SMA) and use **SMAJ26CA (LCSC C19077544)**. Cleaner electrical result, marginal PCB cost.

I owe you the apology — the earlier "SMF30CA is 13 V over abs max" / "SMF24CA is worse" framing was wrong because I was working off a 35 V abs-max number. Against the actual 40 V abs max, SMF24CA is a real fix and SMF30CA is poor but not catastrophic.

Want me to:
1. Just do the BOM-line swap to SMF24CA in the schematic? (no PCB changes)
2. Do the footprint upgrade to SMAJ26CA (footprint reassignment + pour adjustment + DRC re-run)?

---

## Sources

- [SMF30CA — Hongjiacheng / R+O datasheet (LCSC C19077519)](https://www.lcsc.com/datasheet/C19077519.pdf) — actual placed part
- [SMF24CA — MDD / Microdiode datasheet (LCSC C123811)](https://www.lcsc.com/datasheet/C123811.pdf)
- [SMF30CA — DOWO datasheet (LCSC C284106)](https://www.lcsc.com/datasheet/C284106.pdf) — cross-reference, identical numbers
- [Texas Instruments DRV8316C datasheet (SLVSF65)](https://www.ti.com/lit/ds/symlink/drv8316c.pdf) — VM ratings, abs max 35 V, OVP trip ~37 V (table 6.1, 6.3)
