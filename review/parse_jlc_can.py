"""Parse the second JLC capture and filter for CAN-bus-suitable ESD diodes."""
import re, sys, io, csv
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path
from bs4 import BeautifulSoup

src = Path(r"D:\JLC_inf_scroll\jlcpcb_com-parts-2026-05-05-08-30-53.html")
html = src.read_text(encoding="utf-8", errors="replace")
print(f"File size: {len(html):,} chars")

soup = BeautifulSoup(html, "html.parser")
hrefs = soup.find_all("a", href=re.compile(r"/partdetail/[^/]+/C\d+"))
print(f"partdetail anchors: {len(hrefs)}")

seen = {}
for a in hrefs:
    m = re.search(r"/partdetail/[^/]+/(C\d+)", a.get("href", ""))
    if not m:
        continue
    cnum = m.group(1)
    if cnum in seen:
        continue
    seen[cnum] = a

print(f"Unique C-numbers: {len(seen)}")

def row_text(a):
    parent = a
    for _ in range(8):
        parent = parent.parent
        if parent is None:
            break
        text = parent.get_text(" | ", strip=True)
        if "$" in text and len(text) > 80:
            return text
    return a.get_text(" | ", strip=True)

def parse_row(text: str) -> dict:
    fields = {}
    parts = text.split(" | ")
    for p in parts:
        if p in ("Basic", "Preferred", "Extended"):
            fields["tier"] = p
    for i, p in enumerate(parts):
        if p.isdigit() and 0 < int(p) < 10_000_000 and i > 2:
            if i + 1 < len(parts) and "1+" in parts[i+1]:
                fields["stock"] = int(p)
                break
    for p in parts:
        m = re.search(r"\$([\d.]+)", p)
        if m:
            fields["price"] = float(m.group(1))
            break
    for p in parts:
        if "ROHS" in p:
            fields["specs"] = p
            break
    return fields

# Build list
rows = []
for cnum, a in seen.items():
    mpn = a.get_text(strip=True)
    text = row_text(a)
    f = parse_row(text)
    rows.append({"c": cnum, "mpn": mpn, **f, "row": text})

# CAN-suitable: bidirectional, working V ~24-30V, low cap (<50pF), 2-line preferred
def is_can(r):
    s = (r.get("specs") or "").lower()
    if not s: return False
    if "bidirectional" not in s and "?" not in s and "can" not in s and "diodes" not in s:
        # Allow unidirectional CAN-marked parts too
        pass
    # Look for working voltage 18-30V
    has_can_v = bool(re.search(r"\b(1[89]|2[0-9]|3[0-3])v\b", s))
    # Has IEC 61000-4-2
    has_esd = "61000-4-2" in s
    # MPN hint
    mpn_hint = any(k in r["mpn"].upper() for k in ["CAN", "PESD2CAN", "NUP2105", "DESD2CAN", "ESDCAN"])
    return mpn_hint or (has_can_v and has_esd)

# Show all CAN-relevant
print("\n=== CAN bus ESD candidates ===")
matches = [r for r in rows if is_can(r)]
matches.sort(key=lambda r: (r.get("tier") != "Basic",
                             r.get("tier") != "Preferred",
                             r.get("price", 999)))
for r in matches[:25]:
    tier = r.get("tier","?"); stock = r.get("stock","?"); price = r.get("price","?")
    specs = (r.get("specs") or "")[:160]
    print(f"  {r['c']:>10}  {r['mpn']:<26} {tier:<10} stk={stock:<8} ${price}")
    print(f"             {specs}")
    print()

# Also show: any MPN with "CAN" in it regardless of filter
print("\n=== All parts with 'CAN' in MPN ===")
for r in rows:
    if "CAN" in r["mpn"].upper():
        tier = r.get("tier","?"); stock = r.get("stock","?"); price = r.get("price","?")
        specs = (r.get("specs") or "")[:160]
        print(f"  {r['c']:>10}  {r['mpn']:<26} {tier:<10} stk={stock:<8} ${price}")
        print(f"             {specs}")
