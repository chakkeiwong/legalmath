"""Thin adapters to pinned native engines; no replacement reasoning engine."""
from pathlib import Path
from scripts.legal_tool_program import ROOT, RES, OUT, DOC, read, save, ref, command, reserve_network, LIMITS

GO_ADAPTER = r'''
package main
import (
 "encoding/json"
 "os"
 "sort"
 "strings"
 "github.com/carneades/carneades-4/src/engine/dung"
 "github.com/carneades/carneades-4/src/engine/caes"
)
type Case struct { Id string; Ids []string; Attacks [][]string }
type Input struct { Cases []Case }
func names(s dung.ArgSet) []string {
 r:=[]string{}; for a,v:=range s { if v { r=append(r,string(a)) } }; sort.Strings(r); return r
}
func control(id string, standard caes.Standard, assumptions []string, positive, negative float64) map[string]interface{} {
 ag:=caes.NewArgGraph()
 for _,id:=range []string{"request","contrary_evidence","exception","duty","no_duty"} {
  s:=caes.NewStatement(); s.Id=id; s.Text=id; ag.Statements[id]=s
 }
 issue:=caes.NewIssue(); issue.Id="duty_issue"; issue.Standard=standard
 issue.Positions=[]*caes.Statement{ag.Statements["duty"],ag.Statements["no_duty"]}
 ag.Issues[issue.Id]=issue
 for _,s:=range issue.Positions {s.Issue=issue}
 add:=func(id,premise,conclusion string,weight float64,undercut bool) {
  a:=caes.NewArgument(); a.Id=id; a.Premises=[]caes.Premise{{Stmt:ag.Statements[premise],Role:"stipulated"}}
  a.Conclusion=ag.Statements[conclusion]
  a.Scheme=&caes.Scheme{Id:"explicit_weight",Weight:caes.ConstantWeighingFunction(weight)}
  if undercut {a.Undercutter=ag.Statements["exception"]}
  ag.Arguments[id]=a; a.Conclusion.Args=append(a.Conclusion.Args,a)
 }
 add("positive","request","duty",positive,true)
 add("negative","contrary_evidence","no_duty",negative,false)
 ag.Assumptions=assumptions
 l:=ag.GroundedLabelling(); labels:=map[string]string{}
 for id,s:=range ag.Statements {labels[id]=l[s].String()}
 return map[string]interface{}{"id":id,"standard":standard,"assumptions":assumptions,"positive_weight":positive,"negative_weight":negative,"labels":labels}
}
func main() {
 raw,err:=os.ReadFile(os.Args[1]); if err!=nil {panic(err)}; var in Input
 if err=json.Unmarshal(raw,&in);err!=nil {panic(err)}
 rows:=[]map[string]interface{}{}
 for _,c:=range in.Cases {
  args:=[]dung.Arg{}; atks:=map[dung.Arg][]dung.Arg{}
  for _,a:=range c.Ids {args=append(args,dung.Arg(a))}
  for _,e:=range c.Attacks {atks[dung.Arg(e[1])]=append(atks[dung.Arg(e[1])],dung.Arg(e[0]))}
  af:=dung.NewAF(args,atks); preferred:=[][]string{}
  for _,s:=range af.PreferredExtensions() {preferred=append(preferred,names(s))}
  sort.Slice(preferred,func(i,j int)bool{return strings.Join(preferred[i],"\x00")<strings.Join(preferred[j],"\x00")})
  rows=append(rows,map[string]interface{}{"id":c.Id,"grounded":[][]string{names(af.GroundedExtension())},"preferred":preferred})
 }
 controls:=[]map[string]interface{}{
  control("premise-present",caes.PE,[]string{"request"},1,1),
  control("premise-absent",caes.PE,[]string{},1,1),
  control("equal-contrary",caes.PE,[]string{"request","contrary_evidence"},1,1),
  control("exception",caes.PE,[]string{"request","exception"},1,1),
  control("pe-weight",caes.PE,[]string{"request","contrary_evidence"},0.6,0.2),
  control("cce-weight",caes.CCE,[]string{"request","contrary_evidence"},0.6,0.2),
  control("brd-weight",caes.BRD,[]string{"request","contrary_evidence"},0.9,0.2),
 }
 b,err:=json.MarshalIndent(map[string]interface{}{"cases":rows,"caes":controls},"","  ");if err!=nil {panic(err)}
 if err=os.WriteFile(os.Args[2],b,0644);err!=nil {panic(err)}
}
'''

PROLOG_ADAPTER = r'''
:- use_module(library(http/json)).
:- use_module(library(readutil)).
:- initialization(main, main).
main :-
 current_prolog_flag(argv, [Module, Input, Output]),
 use_module(Module), read_file_to_string(Input, Text, []), atom_string(Atom, Text),
 le_input:clear_errors,
 catch((le_input:text_to_logic(Atom, Translation) -> Success=true ; Success=false, Translation=[]),
       Exception, (Success=false, Translation=[], term_string(Exception, ExceptionText))),
 findall(S, (le_input:error_notice(A,B,C,D), term_string(error_notice(A,B,C,D), S)), Errors),
 term_string(Translation, Terms, [quoted(true), numbervars(true)]),
 (var(ExceptionText) -> ExceptionText="" ; true),
 open(Output, write, Stream),
 json_write_dict(Stream, _{parsed:Success, errors:Errors, exception:ExceptionText, translation:Terms}),
 close(Stream).
'''

def record_setup_repair():
    path=OUT/"repairs.json"
    value=read(path) if path.exists() else {"maximum":LIMITS["repair_attempts"],"repairs":[]}
    if not any(r["id"]=="native-setup-r1" for r in value["repairs"]):
        if len(value["repairs"])>=value["maximum"]:raise RuntimeError("Repair budget exhausted")
        value["repairs"].append({"id":"native-setup-r1","reason":"T1 local SWI loader path and multi-root schema archive defects",
            "preserved_failure":"T1/attempt-1/result.json","review":ref(DOC/"t2-review.md")})
        save(path,value)

def carneades(work,cases):
    pin=read(RES/"carneades.json")
    module=work/"carneades-adapter";module.mkdir()
    (module/"main.go").write_text(GO_ADAPTER)
    (module/"go.mod").write_text("module legalmath.local/tooltrial\n\ngo 1.24.1\n\nrequire github.com/carneades/carneades-4 v4.0.0+incompatible\nreplace github.com/carneades/carneades-4 => "+str(ROOT/pin["source"])+"\n")
    env={"GOCACHE":str(RES/"go-cache"),"GOMODCACHE":str(RES/"go-modules"),
         "GOPATH":str(RES/"go-path"),"GOTOOLCHAIN":"local","CGO_ENABLED":"0"}
    go=RES/"go-runtime/go/bin/go"
    reserve_network("Carneades adapter pinned module dependency resolution")
    command([go,"mod","tidy"],module,"dependencies",env=env,cwd=module,timeout=180)
    env["GOPROXY"]="off";env["GOSUMDB"]="off"
    command([go,"build","-o",module/"trial","."],module,"build",env=env,cwd=module,timeout=180)
    save(module/"input.json",{"cases":cases})
    command([module/"trial",module/"input.json",module/"output.json"],module,"run",timeout=90)
    data=read(module/"output.json")
    expected={c["id"]:c["baseline"] for c in cases}
    differences=[r["id"] for r in data["cases"] if any(r[s]!=expected[r["id"]][s] for s in ("grounded","preferred"))]
    labels={r["id"]:r["labels"] for r in data["caes"]}
    target={"premise-present":"in","premise-absent":"out","equal-contrary":"out",
            "exception":"out","pe-weight":"in","cce-weight":"out","brd-weight":"in"}
    control_failures=[name for name,label in target.items() if labels[name]["duty"]!=label]
    return {"status":"PASS" if not differences and not control_failures else "FAILED_CONTROLS",
        "decision":"ADAPT_OPTIONAL_EXPLICIT_SEMANTICS","commit":pin["commit"],
        "matched_cases":len(cases)-len(differences),"differences":differences,
        "caes":data["caes"],"control_failures":control_failures,"raw":ref(module/"output.json"),
        "scope":"Actual Dung and CAES engines. Artificial weights and proof standards are declared inputs; Out is nonacceptance, not legal falsity. No defaults changed."}

def logical_english(work):
    record_setup_repair()
    pin=read(RES/"logical-english.json")
    folder=work/"logical-english";folder.mkdir()
    adapter=folder/"parse.pl";adapter.write_text(PROLOG_ADAPTER)
    source=ROOT/pin["source"]
    valid="""the target language is: prolog.
the templates are:
    *a custodian* has obligation to provide *an assurance*,
    *an authority* requests *an assurance* from *a custodian*.
the knowledge base proposed includes:
A custodian has obligation to provide an assurance
    if SFC requests the assurance from the custodian.
"""
    official="""the target language is: prolog.
the templates are:
    *a person* owns *an asset*,
    *a person* has relevant asset *an asset*.
the knowledge base example includes:
A person has relevant asset an asset
    if the person owns the asset.
"""
    texts={"template-control":official,"proposed-p14":valid,
        "malformed-control":"the templates are: @@@ invalid syntax"}
    env={"SWI_HOME_DIR":str(RES/"swipl/usr/lib/swi-prolog"),
         "LD_LIBRARY_PATH":str(RES/"swipl/usr/lib")}
    command([RES/"swipl/usr/bin/swipl","--version"],folder,"version",env=env,timeout=20)
    rows=[]
    for name,text in texts.items():
        inp=folder/(name+".le");inp.write_text(text)
        out=folder/(name+".json")
        command([RES/"swipl/usr/bin/swipl","-q","-f","none","-s",adapter,"--",source/"le_input.pl",inp,out],
                folder,name+"-parse",env=env,cwd=folder,timeout=45)
        result=read(out)
        accepted=result["parsed"] and not result["errors"] and not result["exception"]
        rows.append({"id":name,"accepted":accepted,**result,"input":ref(inp),"output":ref(out)})
    passed=rows[0]["accepted"] and rows[1]["accepted"] and not rows[2]["accepted"]
    return {"status":"PASS" if passed else "FAILED_CONTROLS","decision":"ADAPT_CONTROLLED_AUTHORING_ONLY",
        "commit":pin["commit"],"cases":rows,
        "scope":"Explicit-template parser only. Proposed conditional omits other paragraph-14 requirements and is not a certified translation or fulfillment judgment."}

def legalruleml(work):
    from scripts.legal_tool_acquire import download
    from scripts.legal_tool_components import external
    record_setup_repair()
    xml=RES/"xml.xsd"
    if not xml.exists():
        metadata=download("https://www.w3.org/2009/01/xml.xsd",xml,maximum=1024*1024)
        save(RES/"xml-schema.json",metadata)
    return external("schema",{},work,"legalruleml")
