"""
Calculate stray capacitance for the HSE crystal on twin28xx.kicad_pcb.

Stray = MCU pin Cin + trace-to-plane cap + pad-to-plane cap + via cap (per side)
"""
import re
import math
from pathlib import Path

pcb = Path(r"D:\gehub\twin28xx\twin28xx\twin28xx.kicad_pcb").read_text(encoding="utf-8")

# --- 1. Trace lengths --------------------------------------------------------
parts = pcb.split("(segment")
n_re = re.compile(r'\(net\s+"([^"]+)"\)')
w_re = re.compile(r"\(width\s+([\d.]+)\)")
l_re = re.compile(r'\(layer\s+"([^"]+)"\)')
s_re = re.compile(r"\(start\s+([\d.\-]+)\s+([\d.\-]+)\)")
e_re = re.compile(r"\(end\s+([\d.\-]+)\s+([\d.\-]+)\)")

hse_segments = {"/RCC_OSC_IN": [], "/RCC_OSC_OUT": []}

for chunk in parts[1:]:
    head = chunk[:600]
    nm = n_re.search(head)
    if not nm or nm.group(1) not in hse_segments:
        continue
    width = float(w_re.search(head).group(1))
    layer = l_re.search(head).group(1)
    s = s_re.search(head); e = e_re.search(head)
    sx, sy = float(s.group(1)), float(s.group(2))
    ex, ey = float(e.group(1)), float(e.group(2))
    length = math.hypot(ex - sx, ey - sy)
    hse_segments[nm.group(1)].append((length, width, layer))

# --- 2. Vias on those nets ---------------------------------------------------
via_re = re.compile(
    r"\(via\b[^()]*?\(at\s+[\d.\-]+\s+[\d.\-]+\)[^()]*?\(size\s+([\d.]+)\)[^()]*?\(net\s+\"([^\"]+)\"\)",
    re.DOTALL,
)
via_parts = pcb.split("(via")
hse_vias = {"/RCC_OSC_IN": 0, "/RCC_OSC_OUT": 0}
for chunk in via_parts[1:]:
    head = chunk[:300]
    nm = n_re.search(head)
    if nm and nm.group(1) in hse_vias:
        hse_vias[nm.group(1)] += 1

# --- 3. Stackup --------------------------------------------------------------
# F.Cu (35um) -> prepreg 0.2104 mm NP-155F 7628 e_r=4.4 -> In1.Cu (GND plane)
H = 0.2104e-3      # m, dielectric thickness top to In1
E_R = 4.4
T_CU = 35e-6       # F.Cu thickness, used for fringing

E_0 = 8.854e-12    # F/m

# --- 4. Microstrip C per-unit-length (Wheeler / Hammerstad) ------------------
def microstrip_C_per_m(W_mm: float, h_m: float = H, er: float = E_R) -> float:
    """Capacitance per meter of a microstrip on FR4-like substrate.

    Uses Hammerstad's effective-er formula and the impedance form,
    then converts to C = sqrt(eps_eff) / (c * Z0).
    """
    W = W_mm * 1e-3
    u = W / h_m
    eps_eff = (er + 1)/2 + (er - 1)/2 * (1 + 12/u)**-0.5
    if u <= 1:
        Z0 = (60/math.sqrt(eps_eff)) * math.log(8/u + u/4)
    else:
        Z0 = (120 * math.pi / math.sqrt(eps_eff)) / (u + 1.393 + 0.667*math.log(u + 1.444))
    c0 = 299_792_458.0
    return math.sqrt(eps_eff) / (c0 * Z0)

# --- 5. Pad capacitance (parallel-plate, no fringing) ------------------------
def pad_C(area_mm2: float, h_m: float = H, er: float = E_R) -> float:
    A = area_mm2 * 1e-6
    return E_0 * er * A / h_m

# Approximate pad areas:
#  - 0402 cap pad: ~1.2 mm x 0.65 mm = 0.78 mm^2 each (2 pads/cap, 1 connects to OSC net)
#  - Crystal X322512MSB4SI (SMD3225-4P) pad: ~1.0 mm x 0.6 mm = 0.60 mm^2
#  - Each OSC net touches 1 crystal pad + 1 cap pad = 1.38 mm^2
PAD_AREA_PER_SIDE = 0.78 + 0.60   # mm^2

# --- 6. Via cap (rough): ~0.3 pF for a 0.3 mm via through 1.6 mm board ------
VIA_C = 0.3e-12  # F

# --- 7. STM32G473 HSE pin input capacitance ---------------------------------
# From STM32G473 datasheet (Rev 8) Table - HSE oscillator characteristics:
#   C_L (load capacitance) = 5 pF typical (this is the spec the IC was designed for)
#   The on-chip OSC_IN and OSC_OUT pin Cin is ~3-4 pF (each).
# We treat MCU_PIN_C as the per-pin input cap added in series with the trace.
MCU_PIN_C = 5e-12  # F per side (conservative; STM32G4 lists ~5 pF total)

# --- 8. Compute & report -----------------------------------------------------
print("=== HSE trace inventory ===")
for net, segs in hse_segments.items():
    total_len = sum(s[0] for s in segs)
    layers = set(s[2] for s in segs)
    widths = set(round(s[1], 3) for s in segs)
    print(f"  {net}: {len(segs)} segs, total {total_len:.2f} mm on {layers}, widths {widths} mm")

print("\n=== Microstrip C per cm (F.Cu, h=0.2104 mm, e_r=4.4) ===")
for w in [0.16, 0.2, 0.25, 0.3, 0.4]:
    print(f"  W = {w} mm: {microstrip_C_per_m(w)*1e12/100:.3f} pF/cm  (Z0 implied)")

print("\n=== Stray C per OSC pin ===")
for net, segs in hse_segments.items():
    # Sum trace cap (only F.Cu segments contribute as microstrip over GND plane)
    trace_C = 0.0
    for length_mm, width_mm, layer in segs:
        if layer == "F.Cu":
            trace_C += microstrip_C_per_m(width_mm) * (length_mm * 1e-3)
        elif layer == "B.Cu":
            # B.Cu has GND on In2.Cu? No — In2 is +3.3V plane. B.Cu nearest plane is In2.
            # For HSE on B.Cu (unusual), estimate similar (h=prepreg between B and In2)
            trace_C += microstrip_C_per_m(width_mm) * (length_mm * 1e-3)
    pad_c = pad_C(PAD_AREA_PER_SIDE)
    via_c = hse_vias[net] * VIA_C
    total = MCU_PIN_C + trace_C + pad_c + via_c
    print(f"  {net}:")
    print(f"    MCU pin Cin             : {MCU_PIN_C*1e12:5.2f} pF")
    print(f"    Trace cap to GND plane  : {trace_C*1e12:5.2f} pF  ({sum(s[0] for s in segs):.1f} mm)")
    print(f"    Pad cap (crystal+Cload) : {pad_c*1e12:5.2f} pF")
    print(f"    Via cap ({hse_vias[net]} vias)        : {via_c*1e12:5.2f} pF")
    print(f"    -------------------------------")
    print(f"    Total Cstray            : {total*1e12:5.2f} pF")

# --- 9. Required external load cap for spec'd CL=20 pF ----------------------
print("\n=== Required external load cap for CL=20 pF crystal ===")
print(f"  Formula: C_load = 2 * (C_L - Cstray)")
for cstray_pF in [4.0, 5.0, 6.0, 7.0, 8.0]:
    c = 2 * (20 - cstray_pF)
    print(f"  Cstray = {cstray_pF} pF -> Cload = {c} pF")
print("\n=== Frequency error with current 20 pF caps ===")
for cstray_pF in [4.0, 5.0, 6.0, 7.0]:
    cl_actual = 20/2 + cstray_pF
    delta = (cl_actual - 20)
    ppm = delta * 10  # ~10 ppm/pF AT-cut
    print(f"  Cstray = {cstray_pF} pF -> CL_actual = {cl_actual} pF, delta = {delta:+} pF, freq offset ~ {ppm:+.0f} ppm")
