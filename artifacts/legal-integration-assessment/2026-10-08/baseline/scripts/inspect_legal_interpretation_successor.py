"""Bounded read-only inventory of retained legal-interpretation successor inputs."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
P0 = ROOT / "artifacts/legal-interpretation-program/2026-10-06-offline-v1/P0/attempt-2"
def read(p): return json.loads(p.read_text())
def main():
    rows=read(P0/"overlay.json")["records"]
    mode=sys.argv[1]
    if mode=="sample":
        r=rows[int(sys.argv[2])]
        op=r["operative"]
        print(json.dumps({"id":r["reading_id"],"role":r["role"],**{k:op[k] for k in ("reading","candidate_repair","questions")}},indent=2))
    elif mode=="readings":
        seen=set();unique=[]
        for row in rows:
            if row["reading_id"] not in seen: unique.append(row);seen.add(row["reading_id"])
        for row in unique[int(sys.argv[2]):int(sys.argv[3])]:
            op=row["operative"];rd=op["original_reading"];repair=op["candidate_repair"] or {}
            print(json.dumps({"id":row["reading_id"],"local_id":rd["local_id"],"statement":rd["statement"],
                "distinction":rd["distinction"],"citations":[c["unit_id"] for c in rd["citations"]],
                "scope":(rd["formalization"] or {}).get("scope"),"result":(rd["formalization"] or {}).get("result"),
                "disposition":op["reading"]["disposition"],"related":repair.get("related_readings")},ensure_ascii=False))
    elif mode=="shapes":
        from collections import Counter
        print("role counts",Counter(r["role"] for r in rows))
        print("dimensions",Counter(d["dimension"] for r in rows for d in (r["operative"]["candidate_repair"] or {}).get("dimensions",[])))
        print("related",json.dumps([{"id":r["reading_id"],"role":r["role"],"related":r["operative"]["candidate_repair"]["related_readings"],
            "explanation":r["operative"]["candidate_repair"]["relationship_explanation"]}
            for r in rows if r["operative"]["candidate_repair"] and r["operative"]["candidate_repair"]["related_readings"]]))
        print("question_shape",json.dumps(rows[0]["operative"]["questions"][:1]))
        print("obligation_shape",json.dumps(rows[0]["operative"]["obligations"][:1]))
        print("packet_shape",list(read(P0/"packet.json")["units"][0]))
    else: raise ValueError("Use sample INDEX, readings START END, or shapes")
if __name__=="__main__": main()
