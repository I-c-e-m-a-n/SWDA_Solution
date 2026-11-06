"""F5–F9 transaction, invocation, replay and admission regressions."""
import copy
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import pytest
from swda_part2c.schemas import StepAnnotation, HumanDecision, Limits, Scenario
from swda_part2c.orchestrator import Orchestrator, scenarios
from swda_part2c.models import adapters
from swda_part2c.analysis import canonical
from swda_part2c.cli import main
from swda_part2c.store import Store


def rows(result,kind): return [r['data'] for r in result['records'] if r['kind']==kind]


def annotation(candidate,child,step,**changes):
    args=dict(run_id=child['run']['id'],candidate_run_id=candidate['run']['id'],step_id=step,
        reviewer='test-human',origin='human',explicit_action=True,expected_version=candidate['run']['version'],
        action='REJECTED',rationale='Synthetic human challenge to this material counterfactual step.')
    args.update(changes); return StepAnnotation(**args)


def decision(candidate,**changes):
    args=dict(run_id=candidate['run']['id'],reviewer='test-human',origin='human',explicit_action=True,
        expected_version=candidate['run']['version'],action='APPROVE_FOR_INVESTIGATION',
        rationale='Synthetic human authorises investigation of this hypothetical pattern.')
    args.update(changes); return HumanDecision(**args)


@pytest.mark.parametrize('kind,action',[('message','REJECTED'),('invocation','DISPUTED'),('message','ACCEPTED')])
def test_f5_child_annotation_is_atomic_and_preserves_traces(approval,candidate,store,kind,action):
    child=candidate['children'][0]; step=next(r['id'] for r in child['records'] if r['kind']==kind)
    before={r['run']['id']:store.records(r['run']['id'],'message') for r in (candidate,*candidate['children'])}
    receipt=approval.annotate(annotation(candidate,child,step,action=action))
    root=store.export(candidate['run']['id']); recorded=store.export(child['run']['id'])['annotations'][0]
    assert receipt['committed'] and recorded['candidate_run_id']==candidate['run']['id']
    assert root['run']['status']==('REVIEW_PENDING' if action=='ACCEPTED' else 'REVISION_REQUESTED')
    assert not root['decisions'] and root['run']['version']==2
    assert all(store.records(run_id,'message')==trace for run_id,trace in before.items())
    if action!='ACCEPTED':
        with pytest.raises(ValueError): approval.decide(decision(root))
        assert store.records(candidate['run']['id'],'trusted_revision')


@pytest.mark.parametrize('bad',['missing_step','wrong_run','wrong_candidate','stale','model','not_explicit','no_reason'])
def test_f5_invalid_child_annotations_rejected(approval,candidate,store,sc,bad):
    child=candidate['children'][0]; step=next(r['id'] for r in child['records'] if r['kind']=='message')
    changes={}
    if bad=='missing_step': changes['step_id']='absent'
    elif bad=='wrong_run': changes['run_id']=candidate['children'][1]['run']['id']
    elif bad=='wrong_candidate': changes['candidate_run_id']=Orchestrator(store).execute(sc)['run']['id']
    elif bad=='stale': changes['expected_version']=0
    elif bad=='model': changes['origin']='model'
    elif bad=='not_explicit': changes['explicit_action']=False
    else: changes['rationale']=''
    with pytest.raises((ValueError,PermissionError)): approval.annotate(annotation(candidate,child,step,**changes))
    assert store.run(candidate['run']['id'])['status']=='REVIEW_PENDING'
    assert not store.export(child['run']['id'])['annotations']


def test_f5_concurrent_annotation_conflict_and_postapproval_history(approval,candidate,store):
    receipt=approval.decide(decision(candidate)); approved=store.export(candidate['run']['id'])
    child=approved['children'][0]; step=next(r['id'] for r in child['records'] if r['kind']=='message')
    def submit(action):
        try: return approval.annotate(annotation(approved,child,step,action=action))
        except ValueError: return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(submit,['REJECTED','DISPUTED']))
    assert sum(r is not None for r in results)==1
    root=store.export(candidate['run']['id'])
    assert root['run']['status']=='REVISION_REQUESTED' and root['decisions']==[receipt]
    assert len(rows(root,'trusted_revision'))==1


@pytest.mark.parametrize('stage',['insert','commit'])
def test_f5_annotation_transaction_rolls_back(approval,candidate,store,stage):
    child=candidate['children'][0]; step=next(r['id'] for r in child['records'] if r['kind']=='invocation')
    with store.connect() as db:
        if stage=='insert':
            db.execute("CREATE TRIGGER annotation_fail BEFORE INSERT ON annotations BEGIN SELECT RAISE(ABORT,'annotation failure'); END")
        else:
            db.executescript('''CREATE TABLE a_parent(id INTEGER PRIMARY KEY);
                CREATE TABLE a_child(id INTEGER REFERENCES a_parent(id) DEFERRABLE INITIALLY DEFERRED);
                CREATE TRIGGER annotation_fail AFTER INSERT ON annotations BEGIN INSERT INTO a_child VALUES(999); END;''')
    with pytest.raises(sqlite3.IntegrityError): approval.annotate(annotation(candidate,child,step))
    assert store.run(candidate['run']['id'])['status']=='REVIEW_PENDING'
    assert store.run(candidate['run']['id'])['version']==1
    assert not store.export(child['run']['id'])['annotations']
    assert not store.records(candidate['run']['id'],'trusted_revision')


def test_f5_cli_explicit_child_step(candidate,store,tmp_path,monkeypatch,capsys):
    import getpass
    path=tmp_path/'reviewers.json'; path.write_text(json.dumps({'reviewers':[getpass.getuser()]}))
    child=candidate['children'][0]; step=next(r['id'] for r in child['records'] if r['kind']=='message')
    assert main(['--db',store.path,'inspect',child['run']['id'],step])==0
    assert json.loads(capsys.readouterr().out)[0]['id']==step
    monkeypatch.setattr('builtins.input',lambda _: 'YES')
    assert main(['--db',store.path,'--reviewers',str(path),'annotate',child['run']['id'],step,'DISPUTED',
                 '--candidate',candidate['run']['id'],'--version','1','--rationale','Synthetic CLI child step challenge.'])==0
    assert store.run(candidate['run']['id'])['status']=='REVISION_REQUESTED'


def assert_lifecycle(result):
    starts=rows(result,'invocation_started'); ends=rows(result,'invocation'); usage=rows(result,'usage')
    assert {s['invocation_id'] for s in starts}=={s['invocation_id'] for s in ends}
    assert len(starts)==len(ends)==len(usage)
    assert next(b['used'] for b in result['budgets'] if b['scope']==result['run']['id'])==len(ends)
    assert all(i['context']['envelope']['run_id']==result['run']['id'] for i in ends)
    assert all(i['schema_version']=='2' and i['script_version']=='scripts-2' for i in ends)


@pytest.mark.parametrize('fault,expected',[('operation','OPERATION_DENIED'),('malformed','SCHEMA_ERROR'),
    ('recipient','POLICY_VIOLATION'),('unsafe','POLICY_VIOLATION')])
def test_f6_every_rejected_call_has_start_terminal_and_digest(store,sc,fault,expected):
    result=Orchestrator(store).execute(sc.model_copy(update={'fault':fault}),'TEST')
    assert result['run']['status']=='BLOCKED'; assert_lifecycle(result)
    assert all(i['outcome']==expected and i['raw_output']=='' and len(i['output_digest'])==64
               and i['error_code'] for i in rows(result,'invocation'))
    assert not rows(result,'message')


def test_f6_oversized_output_only_persists_bounded_diagnostics(store,sc):
    def factory():
        models=adapters(); models['PA'].generate=lambda _: 'SECRET_UNSAFE_PAYLOAD'*2000; return models
    result=Orchestrator(store,model_factory=factory).execute(sc,'TEST'); assert_lifecycle(result)
    terminal=rows(result,'invocation')[0]
    assert terminal['outcome']=='OVERSIZED_OUTPUT' and terminal['raw_output']==''
    assert 'SECRET_UNSAFE_PAYLOAD' not in json.dumps(result)


def test_f6_post_invocation_timeout_is_recorded(store,sc):
    class Clock:
        now=0.0
        def __call__(self): return self.now
    clock=Clock()
    def factory():
        models=adapters(); old=models['PA'].generate
        def generate(ctx):
            out=old(ctx); clock.now=2.; return out
        models['PA'].generate=generate; return models
    result=Orchestrator(store,Limits(seconds=1.),model_factory=factory,clock=clock).execute(sc,'TEST')
    assert result['run']['status']=='BLOCKED'; assert_lifecycle(result)
    assert rows(result,'invocation')[0]['outcome']=='TIMEOUT' and not rows(result,'message')


def test_f6_adapter_exception_and_recovery_keep_complete_lifecycle(store,sc):
    def factory():
        models=adapters()
        def crash(_): raise RuntimeError('Sensitive raw adapter exception text')
        models['PA'].generate=crash; return models
    with pytest.raises(RuntimeError): Orchestrator(store,model_factory=factory).execute(sc)
    recovered=store.recover(); result=store.export(recovered[0]); assert_lifecycle(result)
    assert rows(result,'invocation')[0]['outcome']=='ADAPTER_EXCEPTION'
    assert 'Sensitive raw adapter exception text' not in json.dumps(result)
    assert result['run']['status']=='INCOMPLETE'


@pytest.mark.parametrize('change',[{'origin':'model'},{'reviewer':'stranger'},{'explicit_action':False},
    {'expected_version':0},{'rationale':'               '}])
def test_f7_denied_decisions_are_audited_without_state_change(approval,candidate,store,change):
    with pytest.raises((ValueError,PermissionError)): approval.decide(decision(candidate,**change))
    after=store.export(candidate['run']['id']); assert after['run']==candidate['run'] and not after['decisions']
    events=rows(after,'decision_denied'); assert len(events)==1 and events[0]['outcome']=='DENIED'
    assert not events[0]['success_receipt'] and 'rationale' not in events[0]


def test_f7_concurrent_duplicate_request_has_one_success_and_one_denial(approval,candidate,store):
    def submit(_):
        try: return approval.decide(decision(candidate))
        except ValueError: return None
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(submit,range(2)))
    assert sum(r is not None for r in results)==1
    after=store.export(candidate['run']['id'])
    assert len(after['decisions'])==1 and len(rows(after,'decision_denied'))==1


@pytest.mark.parametrize('stage',['insert','commit'])
def test_f7_rollback_then_separate_denial_audit(approval,candidate,store,stage):
    with store.connect() as db:
        if stage=='insert':
            db.execute("CREATE TRIGGER decision_fail BEFORE INSERT ON decisions BEGIN SELECT RAISE(ABORT,'forced failure'); END")
        else:
            db.executescript('''CREATE TABLE d_parent(id INTEGER PRIMARY KEY);
                CREATE TABLE d_child(id INTEGER REFERENCES d_parent(id) DEFERRABLE INITIALLY DEFERRED);
                CREATE TRIGGER decision_fail AFTER INSERT ON decisions BEGIN INSERT INTO d_child VALUES(999); END;''')
    with pytest.raises(sqlite3.IntegrityError): approval.decide(decision(candidate))
    after=store.export(candidate['run']['id']); assert after['run']==candidate['run'] and not after['decisions']
    assert not rows(after,'human_decision') and len(rows(after,'decision_denied'))==1


def test_f7_audit_write_failure_reported_explicitly(approval,candidate,store):
    with store.connect() as db:
        db.execute("CREATE TRIGGER audit_fail BEFORE INSERT ON records WHEN NEW.kind='decision_denied' BEGIN SELECT RAISE(ABORT,'audit failure'); END")
    with pytest.raises(RuntimeError,match='DECISION_DENIED_AUDIT_PERSISTENCE_FAILED'):
        approval.decide(decision(candidate,origin='model'))
    assert store.run(candidate['run']['id'])['status']=='REVIEW_PENDING' and not store.export(candidate['run']['id'])['decisions']


@pytest.mark.parametrize('field',['classification','summary','contribution','flow','missing_data','source',
    'counterfactual','reviewer','gate','evaluation','policy','config','dependency','invocation'])
def test_f8_each_semantic_mutation_changes_canonical(candidate,field):
    changed=copy.deepcopy(candidate); card=rows(changed,'card')[0]
    if field=='classification': card['classification']='NEW'
    elif field=='summary': card['summary']['text']+=' Altered mechanism.'
    elif field=='contribution': card['contributions'][0]['claim']['text']+=' Altered contribution.'
    elif field=='flow': card['flows'][0]['destination_actor']='EA'
    elif field=='missing_data': card['missing_data']=[]
    elif field=='source': card['summary']['source_ids']=['S5']
    elif field=='counterfactual': rows(changed,'counterfactual')[0]['outcome']='INCONCLUSIVE'
    elif field=='reviewer': rows(changed,'recommendation')[0]['counterfactual_objections']=['Changed objection']
    elif field=='gate': rows(changed,'gate')[0]['passed']=False
    elif field=='evaluation': rows(changed,'evaluation')[0]['passed']=False
    elif field=='policy': rows(changed,'policy')[0]['allowed']=False
    elif field=='config': rows(changed,'snapshots')[0]['limits']['cf']=0
    elif field=='dependency': rows(changed,'message')[1]['response']['contribution']['depends_on']=[]
    elif field=='invocation': rows(changed,'invocation')[0]['outcome']='OPERATION_DENIED'
    assert canonical(candidate)!=canonical(changed)


@pytest.mark.parametrize('name',['two_actor','three_role','single_actor','variation','benign_s5','new_relative'])
def test_f8_replay_is_equivalent_without_mutating_export(store,name):
    a=Orchestrator(store).execute(scenarios()[name]); original=copy.deepcopy(a)
    b=Orchestrator(store).execute(scenarios()[name])
    assert canonical(a)==canonical(b) and a==original
    assert canonical(a)['canonical_version']=='semantic-replay-2'


def test_f8_postreview_canonical_preserves_decision_and_child_annotation_semantics(approval,candidate,store):
    before=canonical(candidate); approval.decide(decision(candidate)); approved=store.export(candidate['run']['id'])
    assert canonical(approved)==before
    changed=copy.deepcopy(approved); changed['decisions'][0]['action']='REJECT'
    assert canonical(changed,post_review=True)!=canonical(approved,post_review=True)
    child=approved['children'][0]; step=next(r['id'] for r in child['records'] if r['kind']=='message')
    approval.annotate(annotation(approved,child,step)); after=store.export(candidate['run']['id'])
    assert canonical(after)==before
    assert canonical(after,post_review=True)!=canonical(approved,post_review=True)


def interrupted_parent(store,sc,limits):
    # Genuine execution interruption after both PA and TA participated. No forged rows.
    def factory():
        models=adapters(); old=models['TA'].generate
        def generate(ctx):
            if ctx.envelope.round==2: raise RuntimeError('synthetic interruption')
            return old(ctx)
        models['TA'].generate=generate; return models
    with pytest.raises(RuntimeError): Orchestrator(store,limits,model_factory=factory).execute(sc)
    with store.connect() as db: run_id=db.execute("SELECT id FROM runs WHERE kind='CANDIDATE' ORDER BY rowid DESC").fetchone()[0]
    assert store.run(run_id)['status']=='RUNNING'
    return run_id


def test_f9_direct_zero_cap_recreates_failed_independent_probe(store,sc):
    limits=Limits(cf=0); parent=interrupted_parent(store,sc,limits); before=store.usage()
    with pytest.raises(ValueError,match='CF_BUDGET_EXHAUSTED'):
        Orchestrator(store,limits).execute(sc,'CF',parent=parent,removed='TA')
    assert not store.export(parent)['children'] and store.usage()==before


def test_f9_direct_limit_and_duplicate_enforced_at_admission(store,sc):
    limits=Limits(cf=2); parent=interrupted_parent(store,sc,limits); orch=Orchestrator(store,limits)
    assert orch.execute(sc,'CF',parent=parent,removed='PA')['run']['status']=='COMPLETE'
    with pytest.raises(ValueError,match='CF_DUPLICATE_REMOVAL'): orch.execute(sc,'CF',parent=parent,removed='PA')
    assert orch.execute(sc,'CF',parent=parent,removed='TA')['run']['status']=='COMPLETE'
    before=store.usage()
    with pytest.raises(ValueError,match='CF_BUDGET_EXHAUSTED'): orch.execute(sc,'CF',parent=parent,removed='TA')
    assert len(store.export(parent)['children'])==2 and store.usage()==before


def test_f9_concurrent_admission_only_one_slot(store,sc):
    limits=Limits(cf=1); parent=interrupted_parent(store,sc,limits)
    def admit(actor):
        try: return Orchestrator(Store(store.path),limits).execute(sc,'CF',parent=parent,removed=actor)
        except ValueError: return None
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(admit,['PA','TA']))
    assert sum(r is not None for r in results)==1
    assert len(store.export(parent)['children'])==1
    assert all(b['used']<=b['cap'] for b in store.usage())


@pytest.mark.parametrize('alteration',['scenario','limits','actor','state','policy','depth','unparticipated','budget'])
def test_f9_invalid_admission_does_not_consume_or_create_child(store,sc,alteration,monkeypatch):
    limits=Limits(); parent=interrupted_parent(store,sc,limits); scenario=sc; removed='TA'
    if alteration=='scenario': scenario=sc.model_copy(update={'seed':sc.seed+1})
    elif alteration=='limits': limits=Limits(cf=1)
    elif alteration=='actor': removed='EA'
    elif alteration=='state': store.finish(parent,'INCOMPLETE')
    elif alteration=='policy':
        from swda_part2c.orchestrator import profiles
        fixed=profiles(); fixed['TA']=fixed['TA'].model_copy(update={'incentive':'changed'})
        monkeypatch.setattr('swda_part2c.orchestrator.profiles',lambda:fixed)
    elif alteration=='depth':
        child=Orchestrator(store).execute(sc,'CF',parent=parent,removed='TA'); parent=child['run']['id']
    elif alteration=='unparticipated':
        scenario=scenarios()['three_role']
        # A valid parent with pinned inputs has not yet dispatched any actor.
        from swda_part2c.schemas import Run
        from swda_part2c.sources import Catalogue
        from swda_part2c.orchestrator import profiles
        run=Run(run_id='no-participation',run_type='CANDIDATE',parent_run_id=None,removed_actor=None,scenario=scenario)
        store.create_run(run,Orchestrator(store).snapshot(scenario,Catalogue(),profiles())); store.budget(run.run_id,48)
        parent=run.run_id; removed='EA'
    else:
        # Consume the persisted parent's remaining budget through the trusted budget API.
        while next(b['used'] for b in store.usage() if b['scope']==parent)<48: store.consume([parent])
    before=store.usage(); children=len(store.export(parent)['children'])
    with pytest.raises(ValueError): Orchestrator(store,limits).execute(scenario,'CF',parent=parent,removed=removed)
    assert len(store.export(parent)['children'])==children and store.usage()==before


@pytest.mark.parametrize('fault',['operation','malformed','recipient','repair'])
def test_f8_replay_includes_negative_and_retry_paths(store,sc,fault):
    scenario=sc.model_copy(update={'fault':fault})
    a=Orchestrator(store).execute(scenario,'TEST'); b=Orchestrator(store).execute(scenario,'TEST')
    assert canonical(a)==canonical(b)


def test_f6_interrupted_started_call_gets_terminal_recovery(store,sc):
    from swda_part2c.schemas import Run
    from swda_part2c.sources import Catalogue
    from swda_part2c.orchestrator import profiles
    from swda_part2c.policy import Gateway
    from swda_part2c.schemas import Envelope
    run=Run(run_id='interrupted-call',run_type='TEST',scenario=sc,parent_run_id=None,removed_actor=None)
    store.create_run(run); store.budget(run.run_id,12)
    env=Envelope(run_id=run.run_id,run_type='TEST',message_id='started-message',parent_message_id=None,
        actor='PA',recipient='TA',purpose='propose',source_ids=sc.sources,policy_version=sc.policy_version,
        source_version=sc.source_version,round=1,turn=1,attempt=0)
    ctx=Gateway(Catalogue(),profiles(),store).dispatch(env,sc)
    store.consume([run.run_id],run_id=run.run_id,invocation={'invocation_id':'interrupted-invocation',
        'context':ctx.model_dump(mode='json'),'schema_version':'2','script_version':'scripts-2'},
        usage={'scopes':[run.run_id],'attempt':0,'message_id':env.message_id,'invocation_id':'interrupted-invocation'})
    assert store.recover()==[run.run_id]
    result=store.export(run.run_id); assert_lifecycle(result)
    assert rows(result,'invocation')[0]['outcome']=='INTERRUPTED'
    assert store.recover()==[]


def test_f6_start_audit_and_consumption_roll_back_together(store,sc):
    with store.connect() as db:
        db.execute("CREATE TRIGGER start_fail BEFORE INSERT ON records WHEN NEW.kind='invocation_started' BEGIN SELECT RAISE(ABORT,'start failure'); END")
    with pytest.raises(sqlite3.IntegrityError): Orchestrator(store).execute(sc,'TEST')
    assert all(b['used']==0 for b in store.usage())
    with store.connect() as db: run_id=db.execute('SELECT id FROM runs').fetchone()[0]
    assert not store.records(run_id,'invocation_started') and not store.records(run_id,'invocation')


def test_f9_concurrent_duplicate_removals_are_unique(store,sc):
    parent=interrupted_parent(store,sc,Limits())
    def admit(_):
        try: return Orchestrator(Store(store.path)).execute(sc,'CF',parent=parent,removed='TA')
        except ValueError: return None
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(admit,range(2)))
    assert sum(r is not None for r in results)==1
    assert len(store.export(parent)['children'])==1
