from pathlib import Path
import shutil
work=Path('/home/chakwong/python/legalmath/artifacts/legal-mission-control/2026-10-26/repaired-retry-continuation')
shutil.copytree(work/'registration-stage',work/'fully-validated-stage')
shutil.copyfile(work/'local-result.json',work/'fully-validated-local-result.json')
print('Full validated program, state, binding, mission and result preserved.')
