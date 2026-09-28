#!/usr/bin/env python3
"""Offline derivative of the pinned Java emitter; never alters the original tree."""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
FILE='compiler/scalc/to_java.ml'


def patch_driver(text):
    start=text.index('  let java\n')
    end=text.index('  let java_cmd =', start)
    block=text[start:end]
    old='    let options = fix_trace options in\n'
    if block.count(old) != 1: raise RuntimeError('Unexpected pinned Java driver')
    # Keep the upstream semantic passes identical to an untraced compilation.
    # Enable observations only after invariant-checked lowering, in Java emission.
    block=block.replace(old, '    let trace = options.Global.trace in\n'
                        '    let options = Global.enforce_options ~trace:None () in\n')
    emit='    Scalc.To_java.format_program ~is_stdlib ~class_name output_file ppf prg'
    if block.count(emit) != 1: raise RuntimeError('Unexpected pinned emission call')
    block=block.replace(emit, '    let _ = Global.enforce_options ~trace () in\n'+emit)
    return text[:start]+block+text[end:]


def patch(text):
    old='''  | EAppOp { op = Log _, _; _ } when Global.options.trace <> None ->
    Message.error "tracing is not yet supported in Java"
'''
    new='''  | EAppOp { op = Log (PosRecordIfTrueBool, _), _; args = [arg1]; _ }
    when Global.options.trace <> None ->
    let pos = Mark.get e in
    fprintf ppf "NativeTrace.condition(%S, %d, %d, %d, %d, %a)"
      (Pos.get_file pos) (Pos.get_start_line pos) (Pos.get_start_column pos)
      (Pos.get_end_line pos) (Pos.get_end_column pos)
      (format_expression ctx) arg1
'''
    if old not in text: raise RuntimeError('Unexpected pinned emitter')
    text=text.replace(old,new)
    start=text.index('  | SIfThenElse\n')
    end=text.index('  | SSpecialOp _ -> .',start)
    block=text[start:end]
    block=block.replace('(format_expression_with_paren ctx)\n      if_expr','(format_native_condition ctx)\n      if_expr')
    block=block.replace('(format_expression ctx) if_expr','(format_native_condition ctx) if_expr')
    block=block.replace('''    let cond_format ppf = fprintf ppf "%a.isNone()" VarName.format switch_var in''','''    let cond_format ppf =
      if Global.options.trace = None then fprintf ppf "%a.isNone()" VarName.format switch_var
      else let pos = Mark.get stmt in
        fprintf ppf "NativeTrace.option(%S, %d, %d, %d, %d, %a.isNone())"
          (Pos.get_file pos) (Pos.get_start_line pos) (Pos.get_start_column pos)
          (Pos.get_end_line pos) (Pos.get_end_column pos) VarName.format switch_var
    in''')
    oldcase='''      fprintf ppf "@[<v 4>case %a: {@ %a%a%t@;<1 -4>}@]" EnumConstructor.format
        enum_cstr format_init_case'''
    newcase='''      let observation ppf =
        if Global.options.trace <> None then
          let pos = Mark.get stmt in
          fprintf ppf "NativeTrace.caseTaken(%S, %d, %d, %d, %d, %S);@ "
            (Pos.get_file pos) (Pos.get_start_line pos) (Pos.get_start_column pos)
            (Pos.get_end_line pos) (Pos.get_end_column pos)
            (Format.asprintf "%a" EnumConstructor.format enum_cstr)
      in
      fprintf ppf "@[<v 4>case %a: {@ %t%a%a%t@;<1 -4>}@]" EnumConstructor.format
        enum_cstr observation format_init_case'''
    if oldcase not in block:raise RuntimeError('Unexpected switch emitter')
    block=block.replace(oldcase,newcase)
    text=text[:start]+block+text[end:]
    point=text.index('and format_expression_with_paren')
    helper='''and format_native_condition ctx ppf e =
  if Global.options.trace = None then format_expression_with_paren ctx ppf e
  else let pos = Mark.get e in
    fprintf ppf "NativeTrace.branch(%S, %d, %d, %d, %d, %a)"
      (Pos.get_file pos) (Pos.get_start_line pos) (Pos.get_start_column pos)
      (Pos.get_end_line pos) (Pos.get_end_column pos)
      (format_expression ctx) e

'''
    text=text[:point]+helper+text[point:]
    return text


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    out=Path(a.out).resolve()
    if out.exists() and any(out.iterdir()): raise RuntimeError('Use a fresh trace toolchain directory')
    out.mkdir(parents=True,exist_ok=True)
    base=ROOT/'.localresources/catala-toolchain'
    locked=json.loads((ROOT/'docs/implementation/catala/toolchain-lock.json').read_text())
    upstream=base/('catala-'+locked['upstream_commit']);source=out/'source'
    # Copy only files in the original lock, with all digests checked.
    for name,h in locked['source_files'].items():
        data=(upstream/name).read_bytes()
        if hashlib.sha256(data).hexdigest()!=h:raise RuntimeError('Upstream changed: '+name)
        target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    diff='';changed={}
    for name, transform in ((FILE,patch),('compiler/driver.ml',patch_driver)):
        before=(source/name).read_text();after=transform(before);(source/name).write_text(after)
        diff+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
        changed[name]=hashlib.sha256(after.encode()).hexdigest()
    (out/'java-trace.patch').write_text(diff)
    switch=base/'opam-root/catala-clean-1.2.1'
    env={k:os.environ[k] for k in ('HOME','USER','LOGNAME','LANG','TMPDIR') if k in os.environ}
    env.update(PATH=str(switch/'bin')+':/usr/bin:/bin',OCAMLPATH=str(switch/'lib'),
               CAML_LD_LIBRARY_PATH=str(switch/'lib/stublibs'),CC='/usr/bin/gcc',CXX='/usr/bin/g++',LC_ALL='C.UTF-8')
    command=[str(switch/'bin/dune'),'build','--profile','release','-j','4','compiler/catala.exe']
    began=time.monotonic()
    with (out/'build.log').open('wb') as log:
        result=subprocess.run(command,cwd=source,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600)
    record={'trace_profile':'java-emitter.v2','invariants':'original_and_instrumented',
            'coverage':'Emitted Java branches, options, variants and scope outputs; external library internals excluded',
            'command':command,'exit_code':result.returncode,'wall_ms':int((time.monotonic()-began)*1000),
            'base_compiler_sha256':locked['compiler_sha256'],'upstream_commit':locked['upstream_commit'],
            'patch_sha256':hashlib.sha256(diff.encode()).hexdigest(),
            'changed_files':changed,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    if result.returncode==0:
        binary=source/'_build/default/compiler/catala.exe';target=out/'catala';shutil.copyfile(binary,target);target.chmod(0o755)
        record['compiler_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
        record['compiler_version']=subprocess.check_output([target,'--version'],text=True).strip()
        # Build external interpreter modules from the same retained sources. The
        # release archive ships these wrapped, whereas interpret loads each module.
        plugins=out/'stdlib/ocaml';plugins.mkdir(parents=True,exist_ok=True)
        record['ocamlopt_sha256']=hashlib.sha256((switch/'bin/ocamlopt').read_bytes()).hexdigest()
        record['interpreter_plugins']={}
        for module in ('decimal_internal','money_internal','date_internal','list_internal'):
            filename=module.capitalize()+'.ml'
            shutil.copyfile(source/'stdlib/ocaml'/ (module+'.ml'),plugins/filename)
            argv=[str(switch/'bin/ocamlopt'),'-I',str(switch/'lib/zarith'),'-I',str(switch/'lib/catala/runtime_ocaml'),
                  '-I',str(switch/'lib/catala/dates_calc'),'-shared','-o',module.capitalize()+'.cmxs',filename]
            subprocess.run(argv,cwd=plugins,env=env,check=True,timeout=60,capture_output=True)
            name='stdlib/ocaml/'+module.capitalize()+'.cmxs'
            record['interpreter_plugins'][name]=hashlib.sha256((out/name).read_bytes()).hexdigest()
    (out/'trace-toolchain.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2));result.check_returncode()

if __name__=='__main__':main()
