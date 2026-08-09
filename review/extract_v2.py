import pypdf, sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path

ds = Path(r"D:\gehub\twin28xx\review\datasheets")

FILES = {
    "AO3401A.pdf": ("VDS", "VGS", "ID", "Absolute", "Continuous", "BVDSS", "Pulsed", "Drain"),
    "FMMT620TA.pdf": ("VCEO", "VCBO", "VEBO", "IC", "I_C", "Absolute", "Collector", "Saturation"),
    "PRS3015-470.pdf": ("Inductance", "Current", "DCR", "Saturation", "Irms", "Isat", "?H", "uH", "mA", "A"),
    "BZT52B5V1S.pdf": ("VR", "Vz", "VRWM", "Power", "Reverse", "IZT", "Zener"),
}

def extract_keys(pdf_path: Path, keywords):
    pdf = pypdf.PdfReader(str(pdf_path))
    print(f"\n{'='*70}\n{pdf_path.name}  ({len(pdf.pages)} pages)\n{'='*70}")
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        page_hits = []
        for line in lines:
            if any(k in line for k in keywords) and len(line) < 250:
                if re.search(r"\b\d+(\.\d+)?\s*(V|mV|A|mA|µA|uA|W|°C|°|µH|nF|pF|µF|nH)\b", line) or \
                   "Absolute" in line or "absolute" in line:
                    safe = line.encode("ascii", "replace").decode("ascii")
                    page_hits.append(safe)
        if page_hits:
            print(f"\n--- p{i+1} ---")
            for l in page_hits[:25]:
                print(f"  {l}")

for fname, kws in FILES.items():
    p = ds / fname
    if p.exists():
        extract_keys(p, kws)
