"""Encoded transport for the existing guarded local-file editor; never runs commands."""
import base64,json,sys
from edit_workspace_files import apply,LIMIT
if len(sys.argv)!=2 or len(sys.argv[1])>2*LIMIT:
    raise ValueError("One bounded base64 JSON edit specification is required")
spec=json.loads(base64.b64decode(sys.argv[1],validate=True))
print(json.dumps({"status":"PASS","edits":apply(spec)},indent=2))
