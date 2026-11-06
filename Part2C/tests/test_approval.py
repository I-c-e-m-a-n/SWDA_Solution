import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import pytest
from pydantic import ValidationError
from swda_part2c.schemas import HumanDecision, StepAnnotation
from swda_part2c.orchestrator import Orchestrator


def request(candidate,**updates):
    args=dict(run_id=candidate['run']['id'],reviewer='test-human',origin='human',explicit_action=True,
              action='APPROVE_FOR_INVESTIGATION',rationale='Synthetic human integration test authorises further investigation.',expected_version=1)
    args.update(updates)
    return HumanDecision(**args)

@pytest.mark.parametrize('action,status',[
    ('APPROVE_FOR_INVESTIGATION','APPROVED_FOR_INVESTIGATION'),('REJECT','REJECTED'),
    ('REQUEST_REVISION','REVISION_REQUESTED')])
def test_human_decision_commits_atomic_receipt(approval,candidate,store,action,status):
    receipt=approval.decide(request(candidate,action=action))
    assert receipt['status']==status and receipt['committed_version']==2
    assert store.run(candidate['run']['id'])['status']==status
    exported=store.export(candidate['run']['id'])
    assert exported['decisions'][0]['decision_id']==receipt['decision_id']
    assert store.records(candidate['run']['id'],'human_decision')
    with pytest.raises(ValueError): approval.decide(request(candidate,action=action))
    assert len(store.export(candidate['run']['id'])['decisions'])==1

@pytest.mark.parametrize('update',[
    {'origin':'model'}, {'reviewer':'stranger'}, {'explicit_action':False},
    {'expected_version':0}, {'rationale':'               '}])
def test_invalid_decisions_denied(approval,candidate,store,update):
    with pytest.raises((ValueError,PermissionError)): approval.decide(request(candidate,**update))
    assert store.run(candidate['run']['id'])['status']=='REVIEW_PENDING'
    assert not store.export(candidate['run']['id'])['decisions']


def test_malformed_action_rejected(candidate):
    with pytest.raises(ValidationError): request(candidate,action='APPROVE')


def test_conflicting_human_decisions(approval,candidate,store):
    def submit(action):
        try: return approval.decide(request(candidate,action=action))
        except ValueError: return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        receipts=list(pool.map(submit,['APPROVE_FOR_INVESTIGATION','REJECT']))
    assert sum(x is not None for x in receipts)==1
    assert len(store.export(candidate['run']['id'])['decisions'])==1
    assert store.run(candidate['run']['id'])['version']==2


def test_sqlite_failure_rolls_back_no_success_receipt(approval,candidate,store):
    with store.connect() as db:
        db.execute("CREATE TRIGGER force_failure BEFORE INSERT ON decisions BEGIN SELECT RAISE(ABORT,'forced disk failure'); END")
    with pytest.raises(sqlite3.IntegrityError,match='forced disk failure'):
        approval.decide(request(candidate))
    assert store.run(candidate['run']['id'])['status']=='REVIEW_PENDING'
    assert store.run(candidate['run']['id'])['version']==1
    assert not store.records(candidate['run']['id'],'human_decision')
    assert not store.export(candidate['run']['id'])['decisions']


def test_missing_or_failed_persisted_gates(approval,candidate,store):
    # Append a failing gate; agent-provided strings cannot cancel it.
    store.record(candidate['run']['id'],'gate',{'name':'execution_integrity','passed':False})
    with pytest.raises(ValueError,match='PERSISTED_GATES_REQUIRED'): approval.decide(request(candidate))
    assert store.run(candidate['run']['id'])['status']=='REVIEW_PENDING'

@pytest.mark.parametrize('kind',['TEST','CF'])
def test_test_and_cf_never_approvable(approval,store,sc,candidate,kind):
    if kind=='TEST': result=Orchestrator(store).execute(sc,'TEST')
    else: result=candidate['children'][0]
    with pytest.raises(ValueError): approval.decide(request(result))
    assert not store.export(result['run']['id'])['decisions']


def test_step_rejection_preserves_history(approval,candidate,store):
    run_id=candidate['run']['id']
    before=store.records(run_id,'message')
    step_id=before[0]['id']
    receipt=approval.annotate(StepAnnotation(run_id=run_id,step_id=step_id,reviewer='test-human',
        origin='human',action='REJECTED',rationale='The structural modelling premise needs independent revision.'))
    assert receipt['committed']
    assert store.records(run_id,'message')==before
    assert store.run(run_id)['status']=='REVISION_REQUESTED'
    with pytest.raises(ValueError): approval.decide(request(candidate))
    assert not store.export(run_id)['decisions']


def test_accepting_step_does_not_approve(approval,candidate,store):
    run_id=candidate['run']['id']
    step=store.records(run_id,'message')[0]['id']
    approval.annotate(StepAnnotation(run_id=run_id,step_id=step,reviewer='test-human',origin='human',action='ACCEPTED',rationale='Scope is accepted for this synthetic test.'))
    assert store.run(run_id)['status']=='REVIEW_PENDING'
    assert not store.export(run_id)['decisions']


def test_annotation_requires_reason_and_human(approval,candidate,store):
    step=store.records(candidate['run']['id'],'message')[0]['id']
    for origin,rationale in [('model','A sufficient stated test rationale.'),('human','')]:
        with pytest.raises((PermissionError,ValueError)):
            approval.annotate(StepAnnotation(run_id=candidate['run']['id'],step_id=step,reviewer='test-human',origin=origin,action='REJECTED',rationale=rationale))
    assert not store.export(candidate['run']['id'])['annotations']


def test_actual_commit_failure_returns_no_receipt(approval,candidate,store):
    # Deferred FK is valid until COMMIT: exercise failure after all approval SQL ran.
    with store.connect() as db:
        db.executescript('''
        CREATE TABLE commit_parent(id INTEGER PRIMARY KEY);
        CREATE TABLE commit_child(id INTEGER REFERENCES commit_parent(id) DEFERRABLE INITIALLY DEFERRED);
        CREATE TRIGGER fail_at_commit AFTER INSERT ON decisions
        BEGIN INSERT INTO commit_child VALUES(987); END;
        ''')
    with pytest.raises(sqlite3.IntegrityError): approval.decide(request(candidate))
    assert store.run(candidate['run']['id'])['status']=='REVIEW_PENDING'
    assert store.run(candidate['run']['id'])['version']==1
    assert store.export(candidate['run']['id'])['decisions']==[]
    assert not store.records(candidate['run']['id'],'human_decision')
