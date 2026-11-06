import getpass
import json
from swda_part2c.cli import main


def test_history_and_individual_inspection(candidate,store,capsys):
    run_id=candidate['run']['id']
    assert main(['--db',store.path,'history',run_id])==0
    result=json.loads(capsys.readouterr().out)
    assert result['run']['id']==run_id and result['children']
    step=store.records(run_id,'message')[0]['id']
    assert main(['--db',store.path,'inspect',run_id,step])==0
    assert json.loads(capsys.readouterr().out)[0]['id']==step


def test_cli_explicit_human_confirmation(candidate,store,tmp_path,monkeypatch,capsys):
    path=tmp_path/'reviewers.json'; path.write_text(json.dumps({'reviewers':[getpass.getuser()]}))
    run_id=candidate['run']['id']
    args=['--db',store.path,'--reviewers',str(path),'decide',run_id,'REQUEST_REVISION',
          '--version','1','--rationale','This synthetic CLI test requires further human revision.']
    monkeypatch.setattr('builtins.input',lambda prompt:'NO')
    assert main(args)==1
    assert store.run(run_id)['status']=='REVIEW_PENDING'
    capsys.readouterr()
    monkeypatch.setattr('builtins.input',lambda prompt:'REQUEST_REVISION')
    assert main(args)==0
    assert store.run(run_id)['status']=='REVISION_REQUESTED'
    assert len(store.export(run_id)['decisions'])==1


def test_cli_export_and_pending(candidate,store,tmp_path,capsys):
    run_id=candidate['run']['id']
    assert main(['--db',store.path,'pending'])==0
    assert json.loads(capsys.readouterr().out)[0]['id']==run_id
    out=tmp_path/'trace.json'
    assert main(['--db',store.path,'export',run_id,'--output',str(out)])==0
    assert json.loads(out.read_text())['run']['id']==run_id
