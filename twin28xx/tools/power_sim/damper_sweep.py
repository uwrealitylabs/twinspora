#!/usr/bin/env python3
"""RC-damper study: replace each 330uF can with a series R + C damper leg
on the same pads. Sweep R_d and C_d, report bus ripple at U14 VM.

Also models the low-profile polymer-chip alternative (ESR acts as damper R).
"""
import os
import re
import subprocess

NGSPICE = 'ngspice'
VBAT = 14.8
IBUS = 5.0
CER_C = 36e-6
CER_ESR = 0.0005
CER_ESL = 0.15e-9

FEEDS = {
    'right': dict(r_feed=0.0056, r_gnd=0.0012, lead_l=1.5e-6, lead_r=0.020),
    'both':  dict(r_feed=0.0032, r_gnd=0.0007, lead_l=0.75e-6, lead_r=0.010),
}


def netlist(feed, fpwm, branch14, branch15, regen=False):
    c = FEEDS[feed]
    T = 1 / fpwm
    ton = 0.5 * T
    if not regen:
        load = f"""
il14 vm14 gnd PULSE(0 {2*IBUS} 1u 60n 60n {ton - 0.12e-6} {T})
il15 vm15 gnd PULSE(0 {2*IBUS} 1u 60n 60n {ton - 0.12e-6} {T})
"""
        analysis = """
.tran 20n 2m 1.6m
.meas tran vpp14 PP v(vm14) from=1.7m to=2m
.meas tran ibatrms RMS i(llead) from=1.7m to=2m
.meas tran ibatavg AVG i(llead) from=1.7m to=2m
.meas tran idmprms RMS i(vd14) from=1.7m to=2m
"""
    else:
        load = """
il14 gnd vm14 PULSE(0 3 0.2m 1u 1u 0.35m 1)
il15 vm15 gnd DC 0
"""
        analysis = """
.tran 100n 0.6m
.meas tran vmax14 MAX v(vm14) from=0.15m to=0.6m
"""
    return f"""* damper study feed={feed} fpwm={fpwm}
vbat bat 0 DC {VBAT}
rbat bat b1 {c['lead_r']}
llead b1 b2 {c['lead_l']}
rfeed b2 u4in {c['r_feed'] + c['r_gnd']}
rfet u4in vm0 0.004
rv14 vm0 vm14 0.0036
rv15 vm0 vm15 0.0024
lc14 vm14 c14a {CER_ESL}
rc14 c14a c14b {CER_ESR}
cc14 c14b gnd {CER_C}
lc15 vm15 c15a {CER_ESL}
rc15 c15a c15b {CER_ESR}
cc15 c15b gnd {CER_C}
{branch14}
{branch15}
{load}
rgndref gnd 0 1u
{analysis}
.end
"""


def damper(nid, node, rd, cd, esl=3e-9):
    """series R+C leg; vd is 0V source for current measurement"""
    return f"""
vd{nid} {node} d{nid}a DC 0
ld{nid} d{nid}a d{nid}b {esl}
rd{nid} d{nid}b d{nid}c {rd}
cd{nid} d{nid}c gnd {cd}
"""


def run(net):
    p = subprocess.run([NGSPICE, '-b'], input=net, capture_output=True, text=True)
    meas = {}
    for line in (p.stdout + p.stderr).splitlines():
        m = re.match(r'^(\w+)\s*=\s*([-+0-9.eE]+)', line.strip())
        if m:
            meas[m.group(1)] = float(m.group(2))
    return meas


print('=== sweep R_d x C_d @ 25kHz, single-side feed (worst normal case) ===')
print('Vpp(mV) at U14 VM; damper leg on each can footprint')
cds = [22e-6, 47e-6, 100e-6, 150e-6, 220e-6]
rds = [0.05, 0.1, 0.15, 0.22, 0.33, 0.47, 1.0]
print('        ' + ''.join(f'C={c*1e6:4.0f}u ' for c in cds))
best = (9e9, None)
for rd in rds:
    row = f'R={rd*1e3:4.0f}m: '
    for cd in cds:
        b14 = damper(14, 'vm14', rd, cd)
        b15 = damper(15, 'vm15', rd, cd)
        m = run(netlist('right', 25e3, b14, b15))
        v = m.get('vpp14', float('nan'))
        row += f'{v*1e3:6.0f} '
        if v < best[0]:
            best = (v, (rd, cd))
    print(row)
print(f'best: {best[0]*1e3:.0f} mVpp at R={best[1][0]}, C={best[1][1]*1e6:.0f}u')

print()
print('=== chosen dampers vs fpwm and feed ===')
CHOICES = [
    ('R=150m + 100uF', 0.15, 100e-6),
    ('R=220m + 47uF', 0.22, 47e-6),
    ('polymer 2x150uF ESR30m (no R)', 0.015, 300e-6),  # 2 chips: ESR/2, 2C
]
for label, rd, cd in CHOICES:
    for feed in ('right', 'both'):
        line = f'{label:32s} {feed:5s}: '
        for f in (20e3, 25e3, 30e3, 50e3):
            b14 = damper(14, 'vm14', rd, cd)
            b15 = damper(15, 'vm15', rd, cd)
            m = run(netlist(feed, f, b14, b15))
            line += f"{f/1e3:3.0f}k:{m.get('vpp14', float('nan'))*1e3:5.0f}mV "
        m = run(netlist(feed, 25e3, b14, b15))
        idmp = m.get('idmprms', float('nan'))
        mr = run(netlist(feed, 25e3, b14, b15, regen=True))
        line += f"| Idmp {idmp:4.2f}Arms Pd {idmp**2*rd:4.2f}W | regen Vmax {mr.get('vmax14', float('nan')):5.2f}V"
        print(line)

print()
print('=== reference: ceramics-only and with-alu @25k right ===')
for label, b in [('ceramics only', ''), ]:
    m = run(netlist('right', 25e3, b, b))
    print(f"{label}: {m.get('vpp14', float('nan'))*1e3:.0f} mVpp")
