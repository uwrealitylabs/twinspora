"""Extract absolute-max and recommended ratings from each part datasheet."""
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import pypdf
from pathlib import Path

ds_dir = Path(r"D:\gehub\twinspora\review\datasheets")

KEYWORDS = {
    "DRV8316.pdf": ("VM", "Absolute", "absolute", "abs max", "VVM", "ABS", "Vbst",
                    "I_OUT", "RMS current", "rms", "continuous", "peak", "BUCK",
                    "Recommended", "recommended", "Operating", "Junction"),
    "WSD4066DN.pdf": ("V(BR)", "VDS", "VGS", "ID", "I_D", "Absolute", "absolute",
                      "max ratings", "Continuous", "RDS", "Drain"),
    "SIT1042ATK_3.pdf": ("VCC", "VIO", "Absolute", "supply"),
    "XC6206.pdf": ("VIN", "VIN ", "Absolute", "abs max", "Operating", "Output Current"),
    "CA-IF1044VD-Q1.pdf": ("VCC", "VIO", "Absolute"),
}

def extract(pdf_path: Path, keywords):
    pdf = pypdf.PdfReader(str(pdf_path))
    print(f"\n{'='*70}\n{pdf_path.name}  ({len(pdf.pages)} pages)\n{'='*70}")
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        page_hits = []
        for line in lines:
            if any(k in line for k in keywords) and len(line) < 250:
                # Only keep lines that contain a unit suggestive of a rating
                if re.search(r"\b\d+(\.\d+)?\s*(V|mV|A|mA|µA|uA|W|°C|kHz|MHz|Hz|µH|nF|pF|µF)\b", line) or \
                   "Absolute" in line or "absolute" in line or "Recommended" in line or "recommended" in line:
                    safe = line.encode("ascii", "replace").decode("ascii")
                    page_hits.append(safe)
        if page_hits:
            print(f"\n--- p{i+1} ---")
            for l in page_hits[:25]:
                print(f"  {l}")

for fname, kws in KEYWORDS.items():
    p = ds_dir / fname
    if p.exists():
        extract(p, kws)
