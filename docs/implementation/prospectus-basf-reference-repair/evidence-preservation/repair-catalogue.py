"""Keep recovery destinations inside each existing restorer's declared scope."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
path = ROOT / "docs/implementation/prospectus-adoption/checkpoint/manifest.json"
before = path.read_bytes()
with (HERE / "checkpoint-manifest-before-scope-repair.json").open("xb") as stream:
    stream.write(before)
catalogue = json.loads(before)
alias_path = "docs/implementation/prospectus-basf-reference-repair/run-002/product.json"
aliases = [row for row in catalogue["files"] if row["path"] == alias_path]
assert len(aliases) == 1
catalogue["files"] = [row for row in catalogue["files"] if row["path"] != alias_path]
assert all(row["path"].startswith("docs/implementation/prospectus-adoption/") for row in catalogue["files"])
path.write_text(json.dumps(catalogue, indent=2) + "\n")
aliases[0]["identical_to"] = "docs/implementation/prospectus-adoption/phases/A1/attempt-008/product.json"
(HERE / "product-aliases.json").write_text(json.dumps({"files": aliases,
    "restore_command": "python3 docs/implementation/prospectus-basf-reference-repair/evidence-preservation/restore-products.py"}, indent=2) + "\n")
shutil.copyfile(ROOT / "docs/implementation/prospectus-basf-scope-repair/evidence-preservation/restore-products.py", HERE / "restore-products.py")
(HERE / "catalogue-repair-receipt.json").write_text(json.dumps({
    "status": "CATALOGUE_SCOPE_REPAIRED; RESTORE_CHECK_PENDING",
    "original_failure": "Archive path outside evidence directory",
    "cause": "New preservation helper placed the focused result outside the adoption restorer's declared destination scope",
    "before_sha256": hashlib.sha256(before).hexdigest(), "after_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    "adoption_products": len(catalogue["files"]), "separate_focused_aliases": len(aliases),
    "archives_and_original_products": "UNCHANGED", "validation": "recovery-validation.json"}, indent=2) + "\n")
print(json.dumps({"adoption_products": len(catalogue["files"]), "focused_aliases": len(aliases)}))
