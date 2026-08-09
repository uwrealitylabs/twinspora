#!/usr/bin/env python3
"""Bus ripple / bulk-cap study for twin28xx (ngspice batch).

Board R values taken from the copper FDM solve (tools/power_sim/solve_power.py):
  feed right: J->U4 5.6m, both: 3.2m ; U4 FET 4m ; VCC U4->U14 3.6m, U4->U15 2.4m
  GND return ~1.2m single / 0.7m both.

Caps per driver:
  ceramics: 6 x 10uF/50V X5R 0805 (GRM21BR61H106) -> ~6uF each at 15V bias
  bulk:     330uF alu (Rubycon 50PX / Panasonic FT), ESR ~80 mOhm, ESL ~5 nH

Loads: each DRV8316 drawing rectangular PWM bus-current pulses,
duty 0.5, amplitude 2*I_BUS (avg = I_BUS), both drivers in phase (worst case).
Regen test: -I step into the bus, watch VM pump-up.
"""
import os
import subprocess
import sys
import re

NGSPICE = 'ngspice'
OUT = sys.argv[1] if len(sys.argv) > 1 else '.'

VBAT = 14.8      # 4S nominal
FPWM = float(os.environ.get('FPWM', 25e3))   # PWM frequency
IBUS = float(os.environ.get('IBUS', 5.0))    # A average bus current per driver
CER_C = 36e-6    # 6 x 6uF effective per driver
CER_ESR = 0.0005
CER_ESL = 0.15e-9
ALU_C = 330e-6
ALU_ESR = 0.080
ALU_ESL = 5e-9
R_FET = 0.004

CASES = []
for feed, (r_feed, r_gnd, lead_l, lead_r) in {
        'right': (0.0056, 0.0012, 1.5e-6, 0.020),
        'both':  (0.0032, 0.0007, 0.75e-6, 0.010)}.items():
    for alu in (True, False):
        CASES.append(dict(feed=feed, alu=alu, r_feed=r_feed, r_gnd=r_gnd,
                          lead_l=lead_l, lead_r=lead_r))


def netlist(c, regen=False):
    T = 1 / FPWM
    ton = 0.5 * T
    alu14 = f"""
ra14 vm14 a14 0.002
la14 a14 a14b {ALU_ESL}
resr14 a14b a14c {ALU_ESR}
ca14 a14c gnd {ALU_C}
ra15 vm15 a15 0.002
la15 a15 a15b {ALU_ESL}
resr15 a15b a15c {ALU_ESR}
ca15 a15c gnd {ALU_C}
""" if c['alu'] else ''
    if not regen:
        load = f"""
il14 vm14 gnd PULSE(0 {2*IBUS} 1u 60n 60n {ton - 0.12e-6} {T})
il15 vm15 gnd PULSE(0 {2*IBUS} 1u 60n 60n {ton - 0.12e-6} {T})
"""
        analysis = f"""
.tran 20n 2m 1.6m
.meas tran vpp14 PP v(vm14) from=1.7m to=2m
.meas tran vavg14 AVG v(vm14) from=1.7m to=2m
.meas tran ibatrms RMS i(llead) from=1.7m to=2m
.meas tran ibatavg AVG i(llead) from=1.7m to=2m
{'.meas tran ialurms RMS i(la14) from=1.7m to=2m' if c['alu'] else ''}
.meas tran icerrms RMS i(lc14) from=1.7m to=2m
"""
    else:
        load = f"""
il14 gnd vm14 PULSE(0 3 0.2m 1u 1u 0.35m 1)
il15 gnd vm15 DC 0
"""
        analysis = """
.tran 100n 0.6m
.meas tran vmax14 MAX v(vm14) from=0.15m to=0.6m
.meas tran vend14 FIND v(vm14) at=0.54m
"""
    return f"""* twin28xx bus ripple - feed {c['feed']} alu={c['alu']} regen={regen}
vbat bat 0 DC {VBAT}
rbat bat b1 {c['lead_r']}
llead b1 b2 {c['lead_l']}
rfeed b2 u4in {c['r_feed'] + c['r_gnd']}
rfet u4in vm0 {R_FET}
rv14 vm0 vm14 0.0036
rv15 vm0 vm15 0.0024
* ceramic banks
lc14 vm14 c14a {CER_ESL}
rc14 c14a c14b {CER_ESR}
cc14 c14b gnd {CER_C}
lc15 vm15 c15a {CER_ESL}
rc15 c15a c15b {CER_ESR}
cc15 c15b gnd {CER_C}
{alu14}
{load}
rgndref gnd 0 1u
{analysis}
.end
"""


def run(net):
    p = subprocess.run([NGSPICE, '-b'], input=net, capture_output=True, text=True)
    meas = {}
    for line in (p.stdout + p.stderr).splitlines():
        m = re.match(r'^(\w+)\s*=\s*([-+0-9.eE]+)', line.strip())
        if m:
            meas[m.group(1)] = float(m.group(2))
    return meas


print(f"assumptions: fpwm={FPWM/1e3:.0f}kHz, Ibus={IBUS}A/driver avg (pulses 0..{2*IBUS}A), "
      f"Vbat={VBAT}V, ceramics {CER_C*1e6:.0f}uF eff/driver, alu {ALU_C*1e6:.0f}uF ESR {ALU_ESR*1e3:.0f}m")
print()
rows = []
for c in CASES:
    m = run(netlist(c))
    mr = run(netlist(c, regen=True))
    label = f"{c['feed']:5s} {'with-alu' if c['alu'] else 'NO-alu  '}"
    vpp = m.get('vpp14', float('nan'))
    ibat = m.get('ibatrms', float('nan'))
    ibatavg = m.get('ibatavg', float('nan'))
    ialu = m.get('ialurms')
    icer = m.get('icerrms', float('nan'))
    vmax = mr.get('vmax14', float('nan'))
    iac = (ibat**2 - ibatavg**2) ** 0.5 if ibat == ibat and ibatavg == ibatavg else float('nan')
    print(f"{label}: VM ripple {vpp*1e3:6.0f} mVpp | bat AC rms {iac:5.2f} A | "
          f"cer rms {icer:4.2f} A | alu rms {('%4.2f' % ialu) if ialu else ' -- '} A | "
          f"regen +3A Vmax {vmax:6.2f} V")
    rows.append((label, vpp, iac, icer, ialu, vmax))
