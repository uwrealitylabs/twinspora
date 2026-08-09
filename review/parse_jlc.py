"""Parse the JLC infinite-scroll HTML capture and extract part rows.

Strategy: parse using BeautifulSoup since the structure uses Vue scoped CSS
classes (data-v-619e0e24). Each part row is a discrete element; the row
contains MPN (anchor with /partdetail/.../Cxxxxx href), package, library
tier (Basic / Preferred / Extended), stock count, and tiered price.
"""
import re
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from pathlib import Path
from bs4 import BeautifulSoup

src = Path(r"D:\JLC_inf_scroll\jlcpcb_com-parts-2026-05-05-07-30-22.html")
html = src.read_text(encoding="utf-8", errors="replace")
soup = BeautifulSoup(html, "html.parser")

# Each part has an <a href="/partdetail/.../Cxxxxx"> tag. Walk up to find the
# row container, then extract the row's text content.
hrefs = soup.find_all("a", href=re.compile(r"/partdetail/[^/]+/C\d+"))
print(f"Found {len(hrefs)} partdetail anchors", file=sys.stderr)

# Get unique parts (the same part may appear in multiple <a> tags)
seen = {}
for a in hrefs:
    m = re.search(r"/partdetail/[^/]+/(C\d+)", a.get("href", ""))
    if not m:
        continue
    cnum = m.group(1)
    if cnum in seen:
        continue
    seen[cnum] = a

print(f"Unique C-numbers: {len(seen)}", file=sys.stderr)

# Walk to row ancestor and extract text
def row_text(a):
    parent = a
    for _ in range(8):
        parent = parent.parent
        if parent is None:
            break
        # Heuristic: the row container has many child elements covering MPN, lib, stock, price
        text = parent.get_text(" | ", strip=True)
        if "Stock" in text or "Library Type" in text or "$" in text and len(text) > 80:
            return text
    return a.get_text(" | ", strip=True)

# Save full table for grepping
out = Path(r"D:\gehub\twin28xx\review\jlc_tvs_table.tsv")
with out.open("w", encoding="utf-8") as f:
    f.write("c_number\tmpn\trow_text\n")
    for cnum, a in seen.items():
        mpn = a.get_text(strip=True)
        text = row_text(a)
        text = text.replace("\n", " ").replace("\t", " ")
        f.write(f"{cnum}\t{mpn}\t{text}\n")

print(f"Wrote {out}", file=sys.stderr)
print(f"\nSample rows (first 5):", file=sys.stderr)
for cnum, a in list(seen.items())[:5]:
    print(f"\n  --- {cnum}: {a.get_text(strip=True)}", file=sys.stderr)
    print(f"  {row_text(a)[:600]}", file=sys.stderr)
