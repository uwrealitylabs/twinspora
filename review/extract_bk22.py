import pypdf, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path

for fname in ["BK22_catalog.pdf", "BK22_flyer.pdf"]:
    p = Path(r"D:\gehub\twin28xx\review\datasheets") / fname
    pdf = pypdf.PdfReader(str(p))
    print(f"\n{'='*70}\n{fname} ({len(pdf.pages)} pages)\n{'='*70}")
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if text.strip():
            print(f"\n--- p{i+1} ---")
            print(text.encode("ascii", "replace").decode("ascii"))
