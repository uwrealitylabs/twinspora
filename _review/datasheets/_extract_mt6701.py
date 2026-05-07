import fitz, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
p = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else None
doc = fitz.open(p)
buf = []
buf.append(f"PDF: {p}\nPages: {len(doc)}\n")
for i, page in enumerate(doc):
    txt = page.get_text()
    buf.append(f"\n===== PAGE {i+1} =====\n{txt}")
text = "".join(buf)
if out:
    with open(out, "w", encoding="utf-8") as f: f.write(text)
    print(f"Wrote {len(text)} chars to {out}")
else:
    print(text)
