"""Fixed pinned acquisitions; isolated local runtimes only."""
import hashlib
import os
from pathlib import Path
import shutil
import tarfile
import urllib.request
import zipfile
from scripts.legal_tool_program import ROOT,OUT,RES,save,read,ref,sha,command,reserve_network,LIMITS

PINS={
 "pyarg":("DaphneOdekerken/PyArg","f907bac94cbdd663839300b3b7523d4d958ff36f"),
 "carneades":("carneades/carneades-4","d19d5431b36da16ffdc2c7ebe4dded784e65b49a"),
 "logical-english":("LogicalContractsOrg/LogicalEnglish","1b31805c917d2e857e95ad66352d1465658fa3e6"),
 "eyecite":("freelawproject/eyecite","0513e7fec46db49d86d9c8f6a854feba231b50a3"),
 "clerc":("abehou/CLERC","6cd120625f6e86187d4f1064170393ac056834b3"),
}
def download(url,path,maximum=128*1024*1024):
    reserve_network(url)
    path.parent.mkdir(parents=True,exist_ok=True)
    request=urllib.request.Request(url,headers={"User-Agent":"LegalMath-bounded-tool-review/1.0"})
    with urllib.request.urlopen(request,timeout=45) as response, path.open("xb") as target:
        total=0
        while chunk:=response.read(1024*1024):
            total+=len(chunk)
            if total>maximum:raise ValueError("Download size bound")
            target.write(chunk)
    return {"url":url,**ref(path),"bytes":total}

def unpack_zip(path,target):
    target.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(path) as archive:
        files=archive.infolist()
        if sum(x.file_size for x in files)>512*1024*1024:raise ValueError("Expanded archive too large")
        for member in files:
            name=Path(member.filename)
            if name.is_absolute() or ".." in name.parts or (member.external_attr>>16)&0o170000==0o120000:
                raise ValueError("Unsafe archive member")
        archive.extractall(target)
    roots=list(target.iterdir())
    if len(roots)!=1 or not roots[0].is_dir():raise ValueError("Unexpected archive root")
    return roots[0]

def run(work):
    RES.mkdir(parents=True,exist_ok=True)
    rows={}
    for name,(repo,commit) in PINS.items():
        done=RES/(name+".json")
        if done.exists():
            rows[name]=read(done)
            if sha(ROOT/rows[name]["archive"]["path"])!=rows[name]["archive"]["sha256"]:
                raise ValueError("Changed downloaded archive")
            continue
        try:
            archive=download("https://codeload.github.com/"+repo+"/zip/"+commit,RES/(name+".zip"))
            source=unpack_zip(ROOT/archive["path"],RES/(name+"-source"))
            licences=[ref(p) for p in source.rglob("*") if p.is_file() and p.name.lower() in ("license","license.txt","copying")]
            rows[name]={"status":"ACQUIRED","commit":commit,"archive":archive,"source":str(source.relative_to(ROOT)),"licences":licences}
            save(done,rows[name])
        except (OSError,ValueError,zipfile.BadZipFile) as exc:
            rows[name]={"status":"ACQUISITION_UNAVAILABLE","error":str(exc),"commit":commit}
        save(work/"acquisition.json",rows)
    total=sum(p.stat().st_size for p in RES.glob("*.zip"))
    if total>LIMITS["download_bytes"]:raise ValueError("Aggregate download budget")
    env=RES/"venv"
    if not (env/"bin/python").exists():
        command([ROOT/".venv/bin/python","-m","venv",env],work,"venv",timeout=60)
    python=env/"bin/python"
    # Exact candidate revisions are acquired above; transitive wheel versions are
    # retained and hashed before installation. No application environment changes.
    wanted=["networkx==3.4.2","lxml==5.4.0","rank-bm25==0.2.2"]
    if rows["eyecite"]["status"]=="ACQUIRED":
        wanted += [str(ROOT/rows["eyecite"]["source"])]
    dependencies={"status":"UNAVAILABLE"}
    wheel=RES/"wheels";wheel.mkdir(exist_ok=True)
    try:
        reserve_network("isolated wheel resolution/build")
        command([python,"-m","pip","wheel","--wheel-dir",wheel,*wanted],work,"wheels",timeout=300)
        size=sum(p.stat().st_size for p in wheel.iterdir() if p.is_file())
        if total+size>LIMITS["download_bytes"]:raise ValueError("Dependency download bound")
        wheels=sorted(wheel.glob("*.whl"))
        command([python,"-m","pip","install","--no-index","--no-deps",*wheels],work,"install-wheels",timeout=120)
        command([python,"-m","pip","freeze"],work,"freeze",timeout=30)
        dependencies={"status":"INSTALLED","python":str(python.relative_to(ROOT)),
                      "wheels":[ref(p) for p in wheels],"bytes":size}
    except (OSError,RuntimeError,ValueError) as exc:
        dependencies={"status":"UNAVAILABLE","error":str(exc)}
    save(RES/"environment.json",dependencies)
    runtimes=prepare_runtimes(work)
    save(work/"environment.json",{"dependencies":dependencies,"runtimes":runtimes})
    retained_bytes=sum(p.stat().st_size for p in RES.rglob("*") if p.is_file() and p.suffix in (".zip",".gz",".whl",".deb"))
    if retained_bytes>LIMITS["download_bytes"]:raise ValueError("Aggregate retained download allowance exceeded")
    return {"status":"ACQUISITIONS_RECORDED","sources":rows,"environment":dependencies,"runtimes":runtimes,"retained_download_bytes":retained_bytes}

def prepare_runtimes(work):
    """Prepare missing compiler/interpreter locally; never use sudo/system install."""
    runtimes={}
    go=RES/"go-runtime/go/bin/go"
    try:
        if not go.exists():
            archive=download("https://go.dev/dl/go1.24.1.linux-amd64.tar.gz",RES/"go1.24.1.tar.gz")
            target=RES/"go-runtime";target.mkdir(exist_ok=True)
            with tarfile.open(ROOT/archive["path"]) as tar:
                members=tar.getmembers()
                if sum(m.size for m in members)>400*1024*1024:raise ValueError("Go expanded size limit")
                for m in members:
                    parts=Path(m.name)
                    if parts.is_absolute() or ".." in parts.parts or not (m.isdir() or m.isfile()):
                        raise ValueError("Unsafe Go archive member")
                tar.extractall(target,filter="data")
        command([go,"version"],work,"go-version",timeout=20)
        runtimes["go"]={"status":"AVAILABLE","executable":str(go.relative_to(ROOT)),"sha256":sha(go)}
    except (OSError,RuntimeError,ValueError) as exc:
        runtimes["go"]={"status":"UNAVAILABLE","error":str(exc)}
    swi=RES/"swipl/usr/bin/swipl"
    try:
        if not swi.exists():
            debs=RES/"debs";debs.mkdir(exist_ok=True)
            reserve_network("local SWI-Prolog deb downloads")
            command(["apt-get","download","swi-prolog-core=8.4.2+dfsg-2ubuntu1",
                     "swi-prolog-core-packages=8.4.2+dfsg-2ubuntu1"],work,"swi-download",cwd=debs,timeout=120)
            for i,p in enumerate(sorted(debs.glob("*.deb"))):
                command(["dpkg-deb","--extract",p,RES/"swipl"],work,"swi-extract-"+str(i),timeout=30)
        environment={"SWI_HOME_DIR":str(RES/"swipl/usr/lib/swi-prolog")}
        command([swi,"--version"],work,"swi-version",env=environment,timeout=20)
        runtimes["swipl"]={"status":"AVAILABLE","executable":str(swi.relative_to(ROOT)),
                          "environment":environment,"sha256":sha(swi)}
    except (OSError,RuntimeError,ValueError) as exc:
        runtimes["swipl"]={"status":"UNAVAILABLE","error":str(exc)}
    schema=RES/"legalruleml.zip"
    try:
        record=download("https://docs.oasis-open.org/legalruleml/legalruleml-core-spec/v1.0/os/legalruleml-core-spec-v1.0-os.zip",schema,maximum=32*1024*1024)
        # OASIS archives may have multiple top-level entries: inspect safely with
        # the same path/size checks; a root shape mismatch remains unavailable.
        root=unpack_zip(schema,RES/"legalruleml-source")
        runtimes["legalruleml"]={"status":"ACQUIRED","archive":record,"source":str(root.relative_to(ROOT))}
    except (OSError,ValueError,zipfile.BadZipFile) as exc:
        runtimes["legalruleml"]={"status":"UNAVAILABLE","error":str(exc)}
    save(RES/"runtimes.json",runtimes)
    return runtimes
