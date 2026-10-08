"""Register the focused repetition repairs in the reversible edit ledger."""
from __future__ import annotations

from difflib import SequenceMatcher
from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / ".localresources/monograph-repetition/baseline"
REGISTRY = ROOT / "docs/monograph/review/revision/text-edits.json"

FILES = {
    "docs/monograph/chapters/03-proof.tex": [
        "Make the second assurance introduction define the narrower middle-link contract from equation (3.1).",
    ],
    "docs/monograph/chapters/04-languages.tex": [
        "Replace the repeated Catala definition in the literature passage with a source-trace review question.",
        "Make the Catala section move from a generic definition to the source-and-semantics problem and worked guard cases.",
        "Begin the SPI subsection with the banking guard rather than another Catala definition, and let the listing introduce its combined conditions.",
        "Make the SPI Catala return a concrete evidence and conformance exercise.",
        "Replace the repeated Stipula glossary with a rental state-machine mapping.",
        "Use the consent pseudocode to test generation identity and source authority.",
    ],
    "docs/monograph/chapters/07-verification.tex": [
        "Turn the repeated evidence-history introduction into a worked correction case.",
        "Replace the repeated default and branch recital with discriminating fixtures.",
        "Apply the state model to an ambiguous withdrawal trace in the finite event profile.",
    ],
    "docs/monograph/chapters/10-operation.tex": [
        "Turn the repeated bitemporal definition into two explicit incident replay questions.",
    ],
}


def main() -> None:
    record = json.loads(REGISTRY.read_text())
    # The focused repair is the final nine entries.  Rebuild that suffix from
    # the protected snapshot so line wrapping or a later source cleanup cannot
    # leave a stale reversible edit in the registry.
    prefix = record["edits"][:35]
    suffix = []
    for relative, reasons in FILES.items():
        current_path = ROOT / relative
        before = (BASE / relative).read_text().splitlines(keepends=True)
        after = current_path.read_text().splitlines(keepends=True)
        replacements = []
        for tag, i1, i2, j1, j2 in SequenceMatcher(None, before, after).get_opcodes():
            if tag == "equal":
                continue
            old = "".join(before[i1:i2])
            new = "".join(after[j1:j2])
            if not old or not new:
                raise RuntimeError(f"Expected replacement-only repair in {relative}: {tag}")
            replacements.append((old, new))
        if len(replacements) != len(reasons):
            raise RuntimeError(f"Expected {len(reasons)} replacements in {relative}, found {len(replacements)}")
        for (old, new), reason in zip(replacements, reasons):
            suffix.append({"path": relative, "old": old, "new": new, "reason": reason})
    if len(suffix) != 11:
        raise RuntimeError(f"Expected eleven focused repairs, found {len(suffix)}")
    record["edits"] = prefix + suffix
    REGISTRY.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    print(f"Registered {len(suffix)} repetition repairs; ledger now contains {len(record['edits'])} edits.")


if __name__ == "__main__":
    main()
