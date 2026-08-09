import pypdf
from pathlib import Path

ds = Path(r"D:\gehub\twin28xx\review\datasheets\SIT1042ATK_3.pdf")
pdf = pypdf.PdfReader(str(ds))
print(f"Pages: {len(pdf.pages)}\n")

keep = ("ESD", "HBM", "MM", "CDM", "61000", "11898", "ISO ", "kV", "fault", "Fault",
        "VBUS", "VIO", "SPLIT", "split", "tolerance", "pin", "Pin", "RXD", "TXD",
        "STB", "STBY", "VCC", "GND", "CANH", "CANL")

for i, page in enumerate(pdf.pages):
    text = page.extract_text() or ""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    page_hits = []
    for line in lines:
        if any(k in line for k in keep) and len(line) < 220:
            safe = line.encode("ascii", "replace").decode("ascii")
            page_hits.append(safe)
    if page_hits:
        print(f"--- Page {i+1} ---")
        for l in page_hits[:30]:
            print(f"  {l}")
        print()
