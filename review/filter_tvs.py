"""Filter JLC TVS catalog for two slots: USB VBUS (5V) and +BATT (~30V bidir)."""
import csv, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path

table = Path(r"D:\gehub\twin28xx\review\jlc_tvs_table.tsv")
rows = []
with table.open(encoding="utf-8") as f:
    reader = csv.DictReader(f, delimiter="\t")
    for r in reader:
        rows.append(r)

print(f"Loaded {len(rows)} rows")

def parse_row(text: str) -> dict:
    """Extract structured fields from the row text."""
    fields = {}
    parts = text.split(" | ")
    fields["all"] = parts
    # Find tier
    for p in parts:
        if p in ("Basic", "Preferred", "Extended"):
            fields["tier"] = p
    # Find stock (a small int between specs and pricing)
    for i, p in enumerate(parts):
        if p.isdigit() and 0 < int(p) < 10_000_000 and i > 2:
            # Stock is usually the int just before "1+"
            if i + 1 < len(parts) and "1+" in parts[i+1]:
                fields["stock"] = int(p)
                break
    # Price (first $X.YYYY token)
    for p in parts:
        m = re.search(r"\$([\d.]+)", p)
        if m:
            fields["price"] = float(m.group(1))
            break
    # Specs blob is the long one with ROHS in it
    for p in parts:
        if "ROHS" in p:
            fields["specs"] = p
            break
    return fields

def show(filter_name, predicate, sort_by_price=True):
    print(f"\n=== {filter_name} ===")
    matches = []
    for r in rows:
        f = parse_row(r["row_text"])
        if predicate(r, f):
            matches.append((r, f))
    if sort_by_price:
        matches.sort(key=lambda x: (x[1].get("tier") != "Basic",
                                     x[1].get("tier") != "Preferred",
                                     x[1].get("price", 999)))
    for r, f in matches[:10]:
        tier = f.get("tier", "?")
        stock = f.get("stock", "?")
        price = f.get("price", "?")
        specs = f.get("specs", "")[:140]
        print(f"  {r['c_number']:>10}  {r['mpn']:<22}  {tier:<10}  stk={stock:<8} ${price}")
        print(f"             specs: {specs}")

# --- USB VBUS: 5V working, can be single-line or 4-line USB ESD with VBUS pin
# Typical filter: voltage 5V/5.0V/5.25V mentioned, working voltage <= 6V
def is_vbus(r, f):
    s = (f.get("specs") or "").lower()
    if not s:
        return False
    # Working voltage 5–5.25V, max 6V. Look for "5V", "5.25V", "6V" patterns
    has_5v = re.search(r"\b5(?:\.0|\.25)?v\b", s) or "5v" in s
    has_low_v = bool(re.search(r"\b6v\b|\b6\.5v\b", s))
    has_high_v = bool(re.search(r"\b(1[5-9]|2[0-9]|3[0-9]|4[0-9])v\b", s))
    # Exclude high-voltage TVS (>14V working)
    if has_high_v and not has_5v:
        return False
    # Want low cap for data, but for VBUS only we don't care; still avoid > 50pF
    return bool(has_5v or has_low_v)

# --- +BATT TVS: bidirectional, breakdown ~25–35V (for 24V system), >100W
def is_batt(r, f):
    s = (f.get("specs") or "").lower()
    if "bidirectional" not in s:
        return False
    # Working voltage in 24-30V range
    m_work = re.search(r"\b(2[5-9]|3[0-3])v\b", s)
    if not m_work:
        return False
    # Want serious power, ≥100W
    m_pwr = re.search(r"(\d{3,4})w", s)
    if not m_pwr:
        return False
    pwr = int(m_pwr.group(1))
    return pwr >= 100

show("Candidates for USB VBUS (5V working)", is_vbus)
show("Candidates for +BATT TVS (24-33V bidirectional, ≥100W)", is_batt)

# Tier breakdown — what's Basic / Preferred at all in this catalog?
print("\n=== All Basic/Preferred TVS in the captured catalog ===")
for r in rows:
    f = parse_row(r["row_text"])
    tier = f.get("tier")
    if tier in ("Basic", "Preferred"):
        specs = (f.get("specs") or "")[:130]
        print(f"  {r['c_number']:>10}  {r['mpn']:<22}  {tier:<10}  ${f.get('price','?')}  {specs}")
