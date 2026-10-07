
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
