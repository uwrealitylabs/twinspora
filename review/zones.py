import re
import collections
from pathlib import Path

pcb = Path(r"D:\gehub\twinspora\twinspora\twinspora.kicad_pcb").read_text(encoding="utf-8")

# Find each top-level zone block. They start with "\t(zone\n" at column 1 (one tab).
zone_starts = [m.start() for m in re.finditer(r"^\t\(zone\n", pcb, re.MULTILINE)]
print(f"Top-level zones found: {len(zone_starts)}")

# Take a slice from each start to next zone-or-end-of-file, then read first few lines.
zone_starts.append(len(pcb))
chunks = [pcb[zone_starts[i]:zone_starts[i+1]] for i in range(len(zone_starts)-1)]

n_re = re.compile(r'\(net\s+"([^"]+)"\)')
ly_re = re.compile(r'\(layer\s+"([^"]+)"\)')
lys_re = re.compile(r'\(layers\s+([^)]+)\)')

by_net_layer = collections.Counter()
for ch in chunks:
    head = ch[:2000]
    nm = n_re.search(head)
    if not nm:
        continue
    layers = []
    lm = ly_re.search(head)
    if lm:
        layers = [lm.group(1)]
    else:
        lmm = lys_re.search(head)
        if lmm:
            layers = re.findall(r'"([^"]+)"', lmm.group(1))
    for L in layers:
        by_net_layer[(nm.group(1), L)] += 1

print(f"\n{'Net':<22} {'Layer':<10} {'Count':>5}")
print("-"*42)
nets = sorted(set(k[0] for k in by_net_layer))
for net in nets:
    for L in ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu"):
        c = by_net_layer.get((net, L), 0)
        if c:
            print(f"{net[:22]:<22} {L:<10} {c:>5}")
