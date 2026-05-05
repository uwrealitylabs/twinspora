import re
import pypdf
from pathlib import Path

ds = Path(r"D:\gehub\twinspora\review\datasheets")

for name in ["XC6206.pdf", "CA-IF1044VD-Q1.pdf"]:
    pdf = pypdf.PdfReader(str(ds / name))
    print(f"\n=== {name} ({len(pdf.pages)} pages) ===")
    keywords = ["F", "uF", "μF", "µF", "Ceramic", "ceramic", "CIN", "COUT", "C IN", "C OUT",
                "decoupling", "Decoupling", "Bypass", "bypass", "VCC", "VIO", "Bulk",
                "Application", "Recommended", "Typical"]
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        # Print short lines that mention caps or applications
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for j, line in enumerate(lines):
            low = line.lower()
            if (("F" in line and ("uf" in low or "μf" in low or "µf" in low or "nf" in low or "pf" in low))
                and len(line) < 200):
                safe = line.encode("ascii", "replace").decode("ascii")
                print(f"  p{i+1}: {safe}")
