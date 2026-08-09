import re
import collections
from pathlib import Path

pcb = Path(r"D:\gehub\twin28xx\twin28xx\twin28xx.kicad_pcb").read_text(encoding="utf-8")

parts = pcb.split("(segment")
n_re = re.compile(r'\(net\s+"([^"]+)"\)')
w_re = re.compile(r"\(width\s+([\d.]+)\)")

by_net_widths = collections.defaultdict(collections.Counter)
for chunk in parts[1:]:
    head = chunk[:500]
    nm = n_re.search(head)
    wm = w_re.search(head)
    if nm and wm:
        by_net_widths[nm.group(1)][round(float(wm.group(1)), 3)] += 1

print(f"All {len(by_net_widths)} nets with widths:")
for net in sorted(by_net_widths):
    counts = by_net_widths[net]
    width_str = ", ".join(f"{w}mm:{c}" for w, c in sorted(counts.items()))
    total = sum(counts.values())
    print(f"  {net:<35} {total:>4} segs  [{width_str}]")
