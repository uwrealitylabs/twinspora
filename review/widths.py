import re
import collections
from pathlib import Path

pcb = Path(r"D:\gehub\twin28xx\twin28xx\twin28xx.kicad_pcb").read_text(encoding="utf-8")

# Split file on "(segment" markers, take everything up to next "(segment" or matching close.
# Segments are short blocks ~ 200 chars. Easier: regex each field independently within a chunk.
parts = pcb.split("(segment")
print(f"Found {len(parts)-1} segment chunks")

w_re = re.compile(r"\(width\s+([\d.]+)\)")
l_re = re.compile(r'\(layer\s+"([^"]+)"\)')
n_re = re.compile(r'\(net\s+"([^"]+)"\)')

by_net = collections.defaultdict(list)
for chunk in parts[1:]:
    # Take only up to next ")" at end of segment block — segment blocks end with a ")" at start of line
    # Cap chunk to first ~500 chars for safety
    head = chunk[:500]
    wm = w_re.search(head)
    lm = l_re.search(head)
    nm = n_re.search(head)
    if wm and lm and nm:
        by_net[nm.group(1)].append((float(wm.group(1)), lm.group(1)))

# Power nets of interest
power_keys = ["VBUS", "VBAT", "VBATT", "BATT", "+5V", "5V", "+3V3", "3V3", "VM", "VCC",
              "PHA", "PHB", "PHC", "BUCK", "VBAT", "GND"]

print(f"Total nets with segments: {len(by_net)}")
print(f"Total segments: {sum(len(v) for v in by_net.values())}\n")

print(f"{'Net':<30} {'Cnt':>4} {'Widths(mm) x count':<40} {'Layers'}")
print("-" * 110)
nets = sorted(by_net.keys())

interesting = [n for n in nets if any(k.upper() in n.upper() for k in power_keys)]
for net in interesting:
    segs = by_net[net]
    widths = collections.Counter(round(w, 3) for w, _ in segs)
    layers = collections.Counter(l for _, l in segs)
    width_str = ", ".join(f"{w}×{c}" for w, c in sorted(widths.items()))
    layer_str = ", ".join(f"{l}:{c}" for l, c in layers.most_common())
    print(f"{net[:30]:<30} {len(segs):>4} {width_str[:38]:<40} {layer_str}")

print("\n\nGlobal width histogram (mm):")
all_widths = collections.Counter()
for segs in by_net.values():
    for w, _ in segs:
        all_widths[round(w, 3)] += 1
for w, c in sorted(all_widths.items()):
    print(f"  {w:>6} mm : {c}")
