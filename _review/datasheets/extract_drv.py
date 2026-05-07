import fitz, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
doc = fitz.open(r"D:\gehub\twinspora\_review\datasheets\DRV8316C_TI.pdf")
print(f"PAGES: {len(doc)}")
keywords = ["Absolute Maximum", "absolute maximum", "RDS", "R_DS", "RDSon", "RDS(ON)", "RDS(on)", "Thermal Information", "Thermal Resistance", "RthJA", "Junction-to-ambient", "junction-to-ambient", "Recommended Operating", "Operating Conditions", "Maximum continuous output", "VVM", "Supply voltage", "supply voltage"]
target_keywords = ["RDS", "high-side and low-side MOSFET", "On resistance", "ON resistance", "MOSFET ON", "Output transistor", "OUTPUT TRANSISTOR"]
for i in range(len(doc)):
    text = doc[i].get_text()
    if any(k in text for k in target_keywords):
        print(f"=== PAGE {i+1} ===")
        print(text[:4000])
        print("...(truncated)" if len(text) > 4000 else "")
        print()
