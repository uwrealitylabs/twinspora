"""
Fix library paths in twin28xx.kicad_pcb and fp-lib-table.

Problem: The actual disk dirs use double-underscore '__C' (e.g. Inductor__C.pretty,
BEAD__C.3dshapes), but cached footprint 3D-model paths and fp-lib-table URIs use
single-underscore '_C'. Also, many cached model paths use '../../packages3d/...'
relative paths that can't resolve from a footprint embedded in the .kicad_pcb cache.

This script:
  1. Rewrites broken 3D model paths in .kicad_pcb:
     - ${KIPRJMOD}/library/packages3d/<NAME>_C.3dshapes/ -> __C
     - ../../packages3d/<NAME>_C.3dshapes/             -> ${KIPRJMOD}/library/packages3d/<NAME>__C
  2. Rewrites fp-lib-table URIs from <NAME>_C.pretty -> <NAME>__C.pretty
  3. Verifies every rewritten path resolves to an actual file/dir before saving.

Safe by design: dry-run summarises changes; pass --apply to write them.
"""

import re
import sys
from pathlib import Path

PROJECT = Path(r"D:\gehub\twin28xx\twin28xx")
PCB = PROJECT / "twin28xx.kicad_pcb"
FPTBL = PROJECT / "fp-lib-table"
PKG3D_ROOT = PROJECT / "library" / "packages3d"
FP_ROOT = PROJECT / "library" / "footprints"

apply = "--apply" in sys.argv


def fix_pcb_models(text: str):
    """Return (new_text, changes, errors)."""
    changes, errors = [], []

    # Pattern 1: ${KIPRJMOD}/library/packages3d/<NAME>_C.3dshapes/<file>
    # Only fix when the underscore-before-C is preceded by a non-underscore char.
    pat1 = re.compile(
        r'(\$\{KIPRJMOD\}/library/packages3d/)([^/"\s]+?)(?<!_)_C\.3dshapes/'
    )
    # Pattern 2: ../../packages3d/<NAME>_C.3dshapes/<file>
    pat2 = re.compile(
        r'\.\./\.\./packages3d/([^/"\s]+?)(?<!_)_C\.3dshapes/'
    )

    def fix1(m):
        prefix, name = m.group(1), m.group(2)
        new = f"{prefix}{name}__C.3dshapes/"
        changes.append(("KIPRJMOD-singleC", f"{name}_C", f"{name}__C"))
        return new

    def fix2(m):
        name = m.group(1)
        new = f"${{KIPRJMOD}}/library/packages3d/{name}__C.3dshapes/"
        changes.append(("relative-to-KIPRJMOD", f"../../packages3d/{name}_C", f"${{KIPRJMOD}}/library/packages3d/{name}__C"))
        return new

    new_text = pat1.sub(fix1, text)
    new_text = pat2.sub(fix2, new_text)

    # Verify each unique fixed path exists on disk
    for full in re.findall(r'\$\{KIPRJMOD\}/library/packages3d/[^"\s]+\.(?:step|wrl)', new_text):
        rel = full.replace("${KIPRJMOD}/", "")
        on_disk = PROJECT / rel.replace("/", "\\")
        if not on_disk.exists():
            errors.append(f"MISSING after fix: {full}")

    return new_text, changes, errors


def fix_fptbl(text: str):
    changes, errors = [], []
    pat = re.compile(r'(\$\{KIPRJMOD\}/library/footprints/)([^/"\s]+?)(?<!_)_C\.pretty')

    def fix(m):
        prefix, name = m.group(1), m.group(2)
        changes.append((name + "_C.pretty", name + "__C.pretty"))
        return f"{prefix}{name}__C.pretty"

    new_text = pat.sub(fix, text)

    for line in new_text.splitlines():
        m = re.search(r'\$\{KIPRJMOD\}/library/footprints/([^/")]+)', line)
        if m:
            on_disk = FP_ROOT / m.group(1)
            if not on_disk.exists():
                errors.append(f"MISSING after fix: library/footprints/{m.group(1)}")

    return new_text, changes, errors


def report(label, changes, errors):
    print(f"\n=== {label} ===")
    unique = sorted(set(map(tuple, changes)))
    print(f"  rewrites (unique): {len(unique)}, total occurrences: {len(changes)}")
    for c in unique[:40]:
        print("   ", " -> ".join(c[-2:]) if len(c) >= 2 else c)
    if len(unique) > 40:
        print(f"    ... and {len(unique)-40} more")
    if errors:
        print(f"  ERRORS: {len(errors)}")
        for e in errors[:10]:
            print("   ", e)


# --- Run ---
print(f"Mode: {'APPLY' if apply else 'DRY-RUN (re-run with --apply)'}")

pcb_text = PCB.read_text(encoding="utf-8")
pcb_new, pcb_changes, pcb_errors = fix_pcb_models(pcb_text)
report("twin28xx.kicad_pcb", pcb_changes, pcb_errors)

fptbl_text = FPTBL.read_text(encoding="utf-8")
fptbl_new, fptbl_changes, fptbl_errors = fix_fptbl(fptbl_text)
report("fp-lib-table", fptbl_changes, fptbl_errors)

if pcb_errors or fptbl_errors:
    print("\n!! Path-not-found errors exist. Not writing. Resolve and re-run.")
    sys.exit(1)

total = len(pcb_changes) + len(fptbl_changes)
print(f"\nTotal rewrites planned: {total}")

if apply and total:
    PCB.write_text(pcb_new, encoding="utf-8")
    FPTBL.write_text(fptbl_new, encoding="utf-8")
    print("WROTE: twin28xx.kicad_pcb, fp-lib-table")
elif not apply:
    print("(dry-run; no files written)")
