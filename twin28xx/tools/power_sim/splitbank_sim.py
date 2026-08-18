#!/usr/bin/env python3
"""Split ceramic bank study: per driver, keep a small tight bank at VM
(1x10uF + 100nF, low ESR) and put a damping resistor in series with the
remaining 5x10uF. No aluminum caps anywhere.

Question: how well does R-in-series-with-most-ceramics damp the battery-lead
LC tank, and what does the resistor dissipate?
"""
import re
import subprocess

NGSPICE = 'ngspice'
VBAT = 14.8
IBUS = 5.0

FEEDS = {
    'right': dict(r_feed=0.0056, r_gnd=0.0012, lead_l=1.5e-6, lead_r=0.020),
    'both':  dict(r_feed=0.0032, r_gnd=0.0007, lead_l=0.75e-6, lead_r=0.010),
}

C_TIGHT = 6e-6      # 1x10uF derated, right at VM
C_HF = 0.1e-6       # 100nF
C_DAMPED = 30e-6    # 5x10uF derated, behind the damping R


def bank(nid, node, rd):
    return f"""
* tight bank at {node}
lt{nid} {node} t{nid}a 0.3n
ct{nid} t{nid}a gnd {C_TIGHT}
ch{nid} {node} gnd {C_HF}
* damped bank
vd{nid} {node} d{nid}a DC 0
rd{nid} d{nid}a d{nid}b {rd}
cd{nid} d{nid}b gnd {C_DAMPED}
"""


def netlist(feed, fpwm, rd):
    c = FEEDS[feed]
    T = 1 / fpwm
    ton = 0.5 * T
    return f"""* split bank feed={feed} fpwm={fpwm} rd={rd}
vbat bat 0 DC {VBAT}
rbat bat b1 {c['lead_r']}
llead b1 b2 {c['lead_l']}
rfeed b2 u4in {c['r_feed'] + c['r_gnd']}
rfet u4in vm0 0.004
rv14 vm0 vm14 0.0036
rv15 vm0 vm15 0.0024
{bank(14, 'vm14', rd)}
{bank(15, 'vm15', rd)}
il14 vm14 gnd PULSE(0 {2*IBUS} 1u 60n 60n {ton - 0.12e-6} {T})
il15 vm15 gnd PULSE(0 {2*IBUS} 1u 60n 60n {ton - 0.12e-6} {T})
rgndref gnd 0 1u
.tran 20n 2m 1.6m
.meas tran vpp14 PP v(vm14) from=1.7m to=2m
.meas tran ibatrms RMS i(llead) from=1.7m to=2m
.meas tran ibatavg AVG i(llead) from=1.7m to=2m
.meas tran idmprms RMS i(vd14) from=1.7m to=2m
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


print(f'split bank per driver: tight {C_TIGHT*1e6:.0f}uF+100n at VM, '
      f'R_d + {C_DAMPED*1e6:.0f}uF damped leg; NO alu. Ibus={IBUS}A/driver')
print()
print('=== sweep R_d @ single-side feed ===')
print('R_d     |   20kHz    25kHz    30kHz    50kHz  | Idmp@25k  P_R@25k | bat AC@25k')
for rd in (0.0005, 0.05, 0.1, 0.15, 0.22, 0.33, 0.47, 1.0):
    row = f'{rd*1e3:5.0f}m  |'
    for f in (20e3, 25e3, 30e3, 50e3):
        m = run(netlist('right', f, rd))
        row += f" {m.get('vpp14', float('nan'))*1e3:6.0f}mV"
    m = run(netlist('right', 25e3, rd))
    idmp = m.get('idmprms', float('nan'))
    ibat = m.get('ibatrms', float('nan'))
    ibatavg = m.get('ibatavg', float('nan'))
    iac = (max(ibat**2 - ibatavg**2, 0)) ** 0.5
    row += f' | {idmp:5.2f}A  {idmp**2*rd:6.2f}W | {iac:5.2f}A'
    print(row)

print()
print('=== best R_d, both-side feed check ===')
for rd in (0.15, 0.22, 0.33):
    row = f'{rd*1e3:5.0f}m  |'
    for f in (20e3, 25e3, 30e3, 50e3):
        m = run(netlist('both', f, rd))
        row += f" {m.get('vpp14', float('nan'))*1e3:6.0f}mV"
    print(row)
