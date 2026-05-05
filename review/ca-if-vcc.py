import pypdf
from pathlib import Path

ds = Path(r"D:\gehub\twinspora\review\datasheets\CA-IF1044VD-Q1.pdf")
pdf = pypdf.PdfReader(str(ds))

keep = ("VCC", "VIO", "supply", "Supply", "operating", "Operating", "5V", "3.3V", "3V3",
        "ESD", "61000", "kV", "HBM", "Vsup", "Vio", "min", "max", "typ")

print(f"=== CA-IF1044VD-Q1 ({len(pdf.pages)} pages) ===\n")
for i, page in enumerate(pdf.pages):
    text = page.extract_text() or ""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    page_hits = []
    for line in lines:
        if any(k in line for k in keep) and len(line) < 220:
            safe = line.encode("ascii", "replace").decode("ascii")
            page_hits.append(safe)
    if page_hits and i < 12:
        print(f"--- Page {i+1} ---")
        for l in page_hits[:25]:
            print(f"  {l}")
        print()
