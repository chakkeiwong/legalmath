from legalmath.storage.archive import export_history,import_history
from legalmath.interpretation import Interpretations
from legalmath.interpretation.controller import Controller
from .test_controller import config

def test_archive_restores_bound_history_and_disables_tokens(svc,run,proposal,tmp_path):
    ctl=Controller(svc);ctl.configure('author','cfg',run['run_id'],config(proposal));ctl.drive(run['run_id'])
    expected=svc.read('meaning',run['run_id'])
    path=tmp_path/'archive.zip';export_history(svc.db,path)
    restored=import_history(path,tmp_path/'restored')
    assert Interpretations(restored).read('meaning',run['run_id'])==expected
    assert restored.verify()
