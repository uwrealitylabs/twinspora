"""Check whether the In1.GND filled polygon on B.Cu contains points near U16/U18."""
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open(r'D:\gehub\twin28xx\twin28xx\twin28xx.kicad_pcb', 'r', encoding='utf-8') as f:
    txt = f.read()

# Find the In1.GND zone block and extract all filled_polygon (layer "B.Cu") point sets
m = re.search(r'\(zone\s+\(net\s+"GND"\)[^\(]*\(uuid "8185807c[^)]*\)\s*\(name "In1\.GND"\)', txt)
if not m:
    # alternative: find by name
    pass
start = txt.find('(name "In1.GND")')
end = txt.find('\n\t(zone', start + 1)
if end < 0:
    end = len(txt)
zone = txt[start:end]
print(f"In1.GND zone block length: {len(zone)} chars")

# Find filled_polygon (layer "B.Cu")
def point_in_poly(px, py, poly):
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside

fp_re = re.compile(r'\(filled_polygon\s*\(layer "([^"]*)"\)\s*\(pts((?:[^()]|\([^()]*\))*)\)', re.DOTALL)
pt_re = re.compile(r'\(xy\s+([\d\.\-]+)\s+([\d\.\-]+)\)')

stats = {'F.Cu': 0, 'B.Cu': 0, 'In1.Cu': 0, 'In2.Cu': 0}
hits = {'B.Cu': {'U18': False, 'U16': False}, 'F.Cu': {'U18': False, 'U16': False},
        'In1.Cu': {'U18': False, 'U16': False}, 'In2.Cu': {'U18': False, 'U16': False}}

for fm in fp_re.finditer(zone):
    layer = fm.group(1)
    pts = [(float(a), float(b)) for a, b in pt_re.findall(fm.group(2))]
    if not pts:
        continue
    stats[layer] = stats.get(layer, 0) + 1
    # bounding box quick reject
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    bx = (min(xs), max(xs)); by = (min(ys), max(ys))
    for label, (cx, cy) in (('U18', (95.0, 120.0275)), ('U16', (135.0, 120.0275))):
        if not (bx[0]-1 <= cx <= bx[1]+1 and by[0]-1 <= cy <= by[1]+1):
            continue
        if point_in_poly(cx, cy, pts):
            hits.setdefault(layer, {})[label] = True

print("Filled-polygon counts per layer in In1.GND:", stats)
print("Encoder-center inside In1.GND poly?")
for layer in ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu']:
    print(f"  {layer}: U18={hits[layer]['U18']}  U16={hits[layer]['U16']}")
