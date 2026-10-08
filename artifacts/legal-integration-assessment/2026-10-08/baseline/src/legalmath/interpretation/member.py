"""Isolated deterministic adapter. Reads only its frozen request on stdin; no network."""
import sys
import time
from ..canonical import loads, canonical

def main():
    request=loads(sys.stdin.buffer.read(20*1024*1024+1))
    spec=request['spec']
    adapter=spec['adapter']
    if adapter=='timeout': time.sleep(31)
    if adapter=='unavailable': raise SystemExit(2)
    if adapter=='malformed': result={'release_eligible':True}
    elif request['role']=='inventory': result={'inventory_unit_ids':[u['unit_id'] for u in request['packet']['units']], 'proposals':[]}
    else: result={'inventory_unit_ids':[], 'proposals':spec['proposals']}
    sys.stdout.buffer.write(canonical(result))

if __name__=='__main__': main()
