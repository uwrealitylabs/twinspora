"""Find B.Cu segments within radius R of points (cx,cy) for given net regex."""
import re, math, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open(r'D:\gehub\twin28xx\twin28xx\twin28xx.kicad_pcb', 'r', encoding='utf-8') as f:
    txt = f.read()

# Build a net id -> name table
net_re = re.compile(r'\(net\s+(\d+)\s+"([^"]*)"\)')
nets = {int(m.group(1)): m.group(2) for m in net_re.finditer(txt)}

# Find segments — net field can be either an integer id or a quoted name
seg_re = re.compile(
    r'\(segment\s*\(start\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s*'
    r'\(end\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s*'
    r'\(width\s+([\d\.]+)\)\s*'
    r'\(layer\s+"([^"]*)"\)\s*'
    r'\(net\s+(?:"([^"]*)"|(\d+))\)',
    re.MULTILINE
)

def dist_seg_pt(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx*dx + dy*dy
    if L2 == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
    fx, fy = x1 + t*dx, y1 + t*dy
    return math.hypot(px - fx, py - fy)

def scan(cx, cy, label, R=2.5):
    results = []
    for m in seg_re.finditer(txt):
        x1, y1, x2, y2 = map(float, m.group(1, 2, 3, 4))
        w = float(m.group(5))
        layer = m.group(6)
        if m.group(7) is not None:
            name = m.group(7)
        else:
            netid = int(m.group(8))
            name = nets.get(netid, f"<id{netid}>")
        if layer != "B.Cu":
            continue
        d = dist_seg_pt(cx, cy, x1, y1, x2, y2)
        if d <= R:
            results.append((d, name, w, layer, x1, y1, x2, y2))
    results.sort()
    print(f"\n=== B.Cu segments within {R} mm of {label} ({cx},{cy}) ===")
    seen = set()
    by_net = {}
    for d, name, w, layer, x1, y1, x2, y2 in results:
        by_net.setdefault(name, []).append((d, w, x1, y1, x2, y2))
    for name in sorted(by_net):
        items = by_net[name]
        # min distance, count, widths
        widths = sorted({w for _, w, *_ in items})
        print(f"  {name:<25}  count={len(items):3d}  min_d={items[0][0]:.3f} mm  widths={widths}")
        # show the closest 2
        for d, w, x1, y1, x2, y2 in items[:2]:
            print(f"    d={d:.3f}  w={w}  ({x1:.3f},{y1:.3f})->({x2:.3f},{y2:.3f})")

scan(95.0, 120.0275, "U18", R=2.5)
scan(135.0, 120.0275, "U16", R=2.5)
scan(95.0, 120.0275, "U18-wide", R=6.0)
scan(135.0, 120.0275, "U16-wide", R=6.0)
# Also F.Cu near U18 (the actual encoder layer):
def scan_F(cx, cy, label, R=2.5):
    results = []
    for m in seg_re.finditer(txt):
        x1, y1, x2, y2 = map(float, m.group(1, 2, 3, 4))
        w = float(m.group(5))
        layer = m.group(6)
        if m.group(7) is not None:
            name = m.group(7)
        else:
            netid = int(m.group(8))
            name = nets.get(netid, f"<id{netid}>")
        if layer != "F.Cu":
            continue
        d = dist_seg_pt(cx, cy, x1, y1, x2, y2)
        if d <= R:
            results.append((d, name, w, layer, x1, y1, x2, y2))
    results.sort()
    by_net = {}
    for d, name, w, layer, x1, y1, x2, y2 in results:
        by_net.setdefault(name, []).append((d, w, x1, y1, x2, y2))
    print(f"\n=== F.Cu segments within {R} mm of {label} ({cx},{cy}) ===")
    for name in sorted(by_net):
        items = by_net[name]
        widths = sorted({w for _, w, *_ in items})
        print(f"  {name:<25}  count={len(items):3d}  min_d={items[0][0]:.3f}  widths={widths}")

scan_F(95.0, 120.0275, "U18-Fcu", R=3.5)
scan_F(135.0, 120.0275, "U16-Fcu", R=3.5)
