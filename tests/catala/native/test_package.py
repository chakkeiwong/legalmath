from copy import deepcopy
from pathlib import Path
import time
import zipfile
import pytest
from legalmath.canonical import digest
from legalmath.catala.native.package import export, install, prepare, verify
from legalmath.catala.native.host import NativeAuth, NativeHost
from legalmath.catala.native.runtime import build, verify_cases
from legalmath.errors import LegalMathError
from tests.catala.backend_support import TOOLCHAIN, JDK
from .reference import controls


@pytest.fixture(scope='module')
def package_fixture(tmp_path_factory):
    root=tmp_path_factory.mktemp('package')
    task,candidate,cases=controls()[0]
    builddir=root/'build';build(task,candidate,builddir,JDK,**TOOLCHAIN)
    report=verify_cases(builddir,cases[:2],JDK,compiler=TOOLCHAIN['compiler'])
    packaged=root/'package';h=prepare(builddir,packaged,cases[:2],report)
    return root,task,cases,report,packaged,h


def test_package_is_content_addressed_and_roundtrips(package_fixture):
    root,task,cases,report,packaged,h=package_fixture
    assert verify(packaged,expected_hash=h)['task_hash']==digest(task)
    archive=root/'package.zip';export(packaged,archive,expected_hash=h)
    installed=install(archive,root/'store',expected_hash=h)
    assert verify(installed,expected_hash=h)==verify(packaged,expected_hash=h)


def test_package_corruption_and_archive_traversal_are_rejected(package_fixture):
    root,_,_,_,packaged,h=package_fixture
    target=packaged/'candidate.json';original=target.read_bytes();target.write_bytes(original+b'\n')
    with pytest.raises(LegalMathError): verify(packaged,expected_hash=h)
    target.write_bytes(original)
    hostile=root/'hostile.zip'
    with zipfile.ZipFile(hostile,'w') as z:
        z.writestr('../escape','x')
    with pytest.raises(LegalMathError): install(hostile,root/'store2',expected_hash=h)


def test_host_rejects_revoked_release_and_authenticated_tokens(tmp_path,package_fixture):
    root,task,cases,report,packaged,h=package_fixture
    identities={'admin':['admin'],'engineer':['engineering'],'lawyer':['legal'],'operator':['operations']}
    host=NativeHost(tmp_path/'host.sqlite',identities,JDK)
    release=host.stage('engineer',root/'build',cases[:2],compiler=TOOLCHAIN['compiler'])
    host.approve('engineer',release,'engineering');host.approve('lawyer',release,'legal')
    host.activate('engineer',release,expected_active=None)
    host.set_revision('operator','synthetic','0',expected=None)
    auth=NativeAuth(host)
    now=str(time.time_ns()+10_000_000_000)
    op='operator-token-'+'x'*20
    auth.provision('admin','operator',op,['operations'],expires_ns=now)
    snap=cases[1]['snapshot']
    assert auth.transact(op,'auth-1',snap,expected_release=release)['status']=='VALUE'
    auth.revoke('admin',op)
    with pytest.raises(LegalMathError): auth.transact(op,'auth-2',snap,expected_release=release)
    host.revoke('lawyer',release,'Source review withdrawn')
    with pytest.raises(LegalMathError): host.transact('operator','auth-3',snap,expected_release=release)


@pytest.fixture
def approved_host(tmp_path, package_fixture):
    root,task,cases,report,packaged,h=package_fixture
    identities={'admin':['admin'],'both':['engineering','legal'],'engineer':['engineering'],'lawyer':['legal'],'operator':['operations']}
    host=NativeHost(tmp_path/'host.sqlite',identities,JDK)
    release=host.stage_package('engineer',packaged,expected_hash=h,compiler=TOOLCHAIN['compiler'])
    assert release==h
    auth=NativeAuth(host);tokens={}
    for name in ('both','engineer','lawyer','operator'):
        token=name+'-'+'x'*40;tokens[name]=token
        auth.provision('admin',name,token,identities[name],expires_ns=str(time.time_ns()+60_000_000_000))
    for name,role in [('engineer','engineering'),('lawyer','legal')]:
        review=auth.review(tokens[name],release,role)
        auth.approve(tokens[name],release,role,expected_review=digest(review))
    auth.activate(tokens['engineer'],release,expected_active=None)
    auth.set_revision(tokens['operator'],'synthetic','0',expected=None)
    return host,auth,tokens,release,cases[1]['snapshot']


def test_multiple_credentials_do_not_create_distinct_reviewers(approved_host):
    host,auth,tokens,release,snapshot=approved_host
    second='second-credential-'+'z'*32
    auth.provision('admin','both',second,['legal'],expires_ns=str(time.time_ns()+60_000_000_000))
    review=auth.review(tokens['both'],release,'engineering')
    auth.approve(tokens['both'],release,'engineering',expected_review=digest(review))
    auth.approve(second,release,'legal',expected_review=digest(review))
    with pytest.raises(LegalMathError):auth.transact(tokens['operator'],'same-person',snapshot,expected_release=release)
    with pytest.raises(LegalMathError):auth.approve(second,release,'legal',expected_review='0'*64)
    with pytest.raises(LegalMathError):auth.approve(second,release,'legal')


@pytest.mark.parametrize('mutation',['operator_token','reviewer_token','withdraw','expiry','role_removed'])
def test_commit_rechecks_identity_and_approval(approved_host,monkeypatch,mutation):
    import legalmath.catala.native.host as module
    host,auth,tokens,release,snapshot=approved_host
    original=module.evaluate
    def raced(*args,**kwargs):
        result=original(*args,**kwargs)
        if mutation=='operator_token':auth.revoke('admin',tokens['operator'])
        elif mutation=='reviewer_token':auth.revoke('admin',tokens['lawyer'])
        elif mutation=='withdraw':auth.withdraw(tokens['lawyer'],release,'legal')
        elif mutation=='role_removed':host.identities['lawyer']=[]
        else:
            with host.connect() as db:db.execute("UPDATE package_approvals SET expires_ns='1' WHERE role='legal'")
        return result
    monkeypatch.setattr(module,'evaluate',raced)
    with pytest.raises(LegalMathError):auth.transact(tokens['operator'],'race',snapshot,expected_release=release)
    with host.connect() as db:assert db.execute('SELECT count(*) FROM receipts').fetchone()[0]==0


def test_tokens_survive_restart_without_changing_identity_registry(approved_host):
    host,auth,tokens,release,snapshot=approved_host
    restarted=NativeHost(host.path,deepcopy(host.identities),JDK)
    result=NativeAuth(restarted).transact(tokens['operator'],'restart',snapshot,expected_release=release)
    assert result['status']=='VALUE' and set(restarted.identities)==set(host.identities)
    auth.revoke('admin',tokens['operator'])
    with pytest.raises(LegalMathError):auth.provision('admin','operator',tokens['operator'],['operations'],expires_ns=str(time.time_ns()+60_000_000_000))
    with pytest.raises(LegalMathError):NativeAuth(restarted).replay(tokens['operator'],'restart')


def test_rollback_requires_previous_activation_and_current_reviews(approved_host,package_fixture):
    host,auth,tokens,release,snapshot=approved_host
    root,task,cases,report,packaged,h=package_fixture
    replacement=host.stage('engineer',root/'build',cases[:1],compiler=TOOLCHAIN['compiler'])
    for name,role in [('engineer','engineering'),('lawyer','legal')]:host.approve(name,replacement,role)
    with pytest.raises(LegalMathError):host.rollback('engineer',replacement,expected_active=release)
    host.activate('engineer',replacement,expected_active=release)
    host.rollback('engineer',release,expected_active=replacement)
    host.withdraw('lawyer',replacement,'legal')
    with pytest.raises(LegalMathError):host.rollback('engineer',replacement,expected_active=release)
