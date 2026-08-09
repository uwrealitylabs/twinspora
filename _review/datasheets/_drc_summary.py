import json, sys, io, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
with open(r'D:\gehub\twin28xx\_review\drc.json', 'r', encoding='utf-8') as f:
    d = json.load(f)
print("Top-level keys:", list(d.keys()))
for k in ('schematic_parity','violations','unconnected_items'):
    if k in d:
        print(f"\n--- {k} count={len(d[k])} ---")
        sev = collections.Counter(it.get('severity') for it in d[k])
        types = collections.Counter(it.get('type') for it in d[k])
        print('  severities:', dict(sev))
        print('  top types:', types.most_common(20))
