import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from swda_part2c.orchestrator import Orchestrator, scenarios
from swda_part2c.analysis import canonical
from swda_part2c.schemas import Limits, Message, Run
from swda_part2c.evaluation import evaluate


def records(result,kind):
    return [r['data'] for r in result['records'] if r['kind']==kind]

@pytest.mark.parametrize('name,status,classification,actors',[
    ('two_actor','REVIEW_PENDING','KNOWN',2),('three_role','REVIEW_PENDING','VARIATION',3),
    ('single_actor','REVIEW_PENDING','KNOWN',1),('benign_s5','NO_PATTERN',None,0),
    ('insufficient','NO_PATTERN',None,0),('new_relative','NO_PATTERN',None,0),
    ('variation','REVIEW_PENDING','VARIATION',2)])
def test_full_workflows(store,name,status,classification,actors):
    result=Orchestrator(store).execute(scenarios()[name])
    assert result['run']['status']==status
    cards=records(result,'card')
    if classification:
        assert len(cards)==1 and cards[0]['classification']==classification
        assert len(cards[0]['actors'])==actors
        assert cards[0]['machine_outcome']=='PASS'
        assert cards[0]['evaluation_ids']
        assert all(c['source_ids'] for c in cards[0]['assertions'])
        assert len(result['children'])==actors
    else:
        assert not cards and records(result,'no_pattern')
    assert not result['decisions']


def test_routing_ancestry_and_fresh_cf(candidate):
    ms=records(candidate,'message')
    assert any(m['envelope']['recipient']=='TA' for m in ms)
    ids={m['envelope']['message_id'] for m in ms}
    assert any(m['response']['contribution']['depends_on'] for m in ms)
    for cf in candidate['children']:
        assert cf['run']['id']!=candidate['run']['id'] and cf['run']['parent']==candidate['run']['id']
        meta=json.loads(cf['run']['metadata'])
        removed=meta['removed_actor']
        assert meta['scenario']==json.loads(candidate['run']['metadata'])['scenario']
        reset=records(cf,'context_reset')[0]
        assert reset['fresh_history'] and reset['copied_parent_messages']==[]
        assert reset['excluded_parent_messages']
        for invocation in records(cf,'invocation'):
            ctx=invocation['context']
            assert ctx['envelope']['actor']!=removed
            assert not any(m['envelope']['message_id'] in ids for m in ctx['incoming']+ctx['prior'])
        assert all(m['envelope']['message_id'] not in ids for m in records(cf,'message'))
    assert all(c['outcome']=='MULTI_PARTY_DEPENDENCY' for c in records(candidate,'counterfactual'))


def test_three_role_removal_never_assumes_single(store):
    result=Orchestrator(store).execute(scenarios()['three_role'])
    cfs=records(result,'counterfactual')
    assert len(cfs)==3 and all(c['outcome']=='MULTI_PARTY_DEPENDENCY' for c in cfs)
    assert not any(c['outcome']=='SINGLE_ACTOR_FEASIBILITY' for c in cfs)


def test_replay(store,sc):
    a=Orchestrator(store).execute(sc)
    b=Orchestrator(store).execute(sc)
    assert a['run']['id']!=b['run']['id']
    assert canonical(a)==canonical(b)

@pytest.mark.parametrize('fault,code',[
    ('malformed','SCHEMA_RETRIES_EXHAUSTED'),('recipient','RECEIPT_DENIED'),
    ('sender','RECEIPT_DENIED'),('source','RECEIPT_DENIED'),('unsafe','UNSAFE_OR_UNSUPPORTED_OUTPUT'),
    ('unsupported','UNSAFE_OR_UNSUPPORTED_OUTPUT'),('operation','OPERATION_DENIED'),
    ('reviewer_lookup','LOOKUP_DENIED'),('reviewer_invalid','SCHEMA_RETRIES_EXHAUSTED')])
def test_adversarial_fail_closed(store,sc,fault,code):
    result=Orchestrator(store).execute(sc.model_copy(update={'fault':fault}))
    assert result['run']['status']=='BLOCKED'
    assert not records(result,'card')
    assert any(code in g['reason'] for g in records(result,'gate'))
    if fault not in ('reviewer_lookup','reviewer_invalid'):
        assert not records(result,'message')
    if fault=='operation':
        assert len(records(result,'invocation'))==1
        assert records(result,'invocation')[0]['outcome']=='OPERATION_DENIED'


def test_repair_preserves_scope_and_consumes_calls(store,sc):
    result=Orchestrator(store).execute(sc.model_copy(update={'fault':'repair'}),'TEST')
    assert result['run']['status']=='COMPLETE'
    inv=records(result,'invocation')
    assert sum(i['outcome']=='SCHEMA_ERROR' for i in inv)==4
    for bad in (i for i in inv if i['outcome']=='SCHEMA_ERROR'):
        e=bad['context']['envelope']
        good=next(i for i in inv if i['context']['envelope']['message_id']==e['message_id'] and i['outcome']=='SCHEMA_VALID')
        assert {k:v for k,v in e.items() if k!='attempt'}=={k:v for k,v in good['context']['envelope'].items() if k!='attempt'}
    assert next(b['used'] for b in result['budgets'] if b['scope']==result['run']['id'])==9

@pytest.mark.parametrize('limits,code',[
    (Limits(lineage_calls=2),'CALL_BUDGET_EXHAUSTED'),
    (Limits(turns=1),'TURN_BUDGET_EXHAUSTED'),
    (Limits(rounds=1),'ROUND_BUDGET_EXHAUSTED'),
    (Limits(seconds=0.000000001),'TIMEOUT'),
    (Limits(cf=1),'CF_BUDGET_EXHAUSTED')])
def test_resource_boundaries(store,sc,limits,code):
    result=Orchestrator(store,limits).execute(sc)
    assert result['run']['status']=='BLOCKED'
    assert any(code in g['reason'] for g in records(result,'gate'))
    assert all(b['used']<=b['cap'] for b in result['budgets'])


def test_failed_counterfactual_blocks_release(store,sc):
    # Candidate uses five calls with review; budget six permits partial CF but cannot complete lineage.
    result=Orchestrator(store,Limits(lineage_calls=6)).execute(sc)
    assert result['run']['status']=='BLOCKED'
    assert any(c['outcome']=='INCONCLUSIVE' for c in records(result,'counterfactual'))
    assert not result['decisions']


def test_test_suite_is_independent_and_bounded(store):
    report=evaluate(store)
    assert report['executed']==12 and report['failures']==0 and report['passed']
    suite=next(b for b in report['usage'] if b['scope']==report['suite_id'])
    assert suite['used']<=60
    for result in report['results']:
        run=store.run(result['run_id'])
        assert run['kind']=='TEST' and run['parent'] is None and run['status']!='REVIEW_PENDING'
        assert not store.export(run['id'])['decisions']


def test_suite_budget_cannot_replenish(store):
    report=evaluate(store,Limits(suite_calls=3))
    assert not report['passed']
    assert next(b['used'] for b in report['usage'] if b['scope']==report['suite_id'])<=3


def test_interrupted_execution_recovery(store,sc):
    store.create_run(Run(run_id='interrupted',run_type='CANDIDATE',parent_run_id=None,removed_actor=None,scenario=sc))
    assert store.recover()==['interrupted']
    assert store.run('interrupted')['status']=='INCOMPLETE'
    assert store.recover()==[]
    assert store.records('interrupted','recovery')

@pytest.mark.parametrize('kind',['CF','TEST'])
def test_derived_run_parent_restrictions(store,sc,kind):
    parent=Orchestrator(store).execute(sc,kind='TEST')
    with pytest.raises(ValueError):
        Orchestrator(store).execute(sc,kind,parent=parent['run']['id'],removed='TA')


def test_trace_is_append_only(candidate,store):
    import sqlite3
    before=store.records(candidate['run']['id'])
    with pytest.raises(sqlite3.IntegrityError), store.connect() as db:
        db.execute('DELETE FROM records WHERE run_id=?',(candidate['run']['id'],))
    assert before==store.records(candidate['run']['id'])


def test_inconclusive_surviving_two_roles_blocks_candidate(store):
    from swda_part2c.models import adapters
    def factory():
        models=adapters()
        for actor in ('TA','PA','EA'):
            original=models[actor].generate
            def generate(ctx,original=original):
                out=json.loads(original(ctx))
                out['contribution'].update(material=True,features=list(ctx.scenario.features),depends_on=[],dependency_features={})
                from swda_part2c.grounding import contribution_text, benefit_text
                out['contribution']['claim']['text']=contribution_text(ctx.envelope.actor,ctx.scenario.features)
                out['contribution']['benefit']['text']=benefit_text(ctx.envelope.actor,ctx.scenario.features)
                return json.dumps(out)
            models[actor].generate=generate
        return models
    result=Orchestrator(store,model_factory=factory).execute(scenarios()['three_role'])
    assert result['run']['status']=='BLOCKED'
    assert len(records(result,'counterfactual'))==3
    assert all(c['outcome']=='INCONCLUSIVE' for c in records(result,'counterfactual'))
    assert any(g['name']=='counterfactual_evidence' and not g['passed'] for g in records(result,'gate'))


def test_unexpected_adapter_crash_requires_recovery(store,sc):
    from swda_part2c.models import adapters
    def factory():
        models=adapters()
        def crash(ctx): raise RuntimeError('simulated abrupt interruption')
        models['PA'].generate=crash
        return models
    with pytest.raises(RuntimeError): Orchestrator(store,model_factory=factory).execute(sc)
    recovered=store.recover()
    assert len(recovered)==1 and store.run(recovered[0])['status']=='INCOMPLETE'
    assert not store.export(recovered[0])['decisions']


def test_oversized_model_response_fails_closed(store,sc):
    from swda_part2c.models import adapters
    def factory():
        models=adapters(); models['PA'].generate=lambda ctx:'x'*16001
        return models
    result=Orchestrator(store,model_factory=factory).execute(sc)
    assert result['run']['status']=='BLOCKED' and not records(result,'message')
    assert any(g['reason']=='OUTPUT_SIZE_LIMIT' for g in records(result,'gate'))
