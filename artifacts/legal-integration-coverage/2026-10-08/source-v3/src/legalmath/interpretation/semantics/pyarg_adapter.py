"""The retained PyArg archive cannot be imported as an installed dependency."""
from pathlib import Path

def availability(archive):
    archive=Path(archive)
    required=("LICENSE","src/py_arg/abstract_argumentation_classes/argument.py",
              "src/py_arg/aspic_classes/instantiated_argument.py")
    missing=[p for p in required if not (archive/p).is_file()]
    return {"status":"UNAVAILABLE" if missing else "REQUIRES_PINNED_RUNTIME_CHECK",
            "missing":missing,"selected_adapter":"local-finite-acyclic.v1",
            "equivalence_to_pyarg":"NOT_ESTABLISHED",
            "ordering":"explicit all-pairs strict domination; not a claim of PyArg elitist equivalence"}
