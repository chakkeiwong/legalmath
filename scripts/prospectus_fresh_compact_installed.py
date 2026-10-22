"""Use the reviewed installed comparator with explicit repaired destinations."""
import sys
from pathlib import Path
root=Path(sys.argv[1]);sys.path[:0]=[str(root)]
from scripts import prospectus_fresh_compact as repair
repair.bind_runner()
source=root/'scripts/prospectus_fresh_installed.py'
exec(compile(source.read_text(),str(source),'exec'),{'__name__':'__main__','__file__':str(source)})
