"""Independent assessment boundary probes, retained as executable regressions."""
import json
from pathlib import Path
import pytest
from swda_part2c.schemas import Limits, Scenario, Run
from swda_part2c.sources import Catalogue, ROOT
from swda_part2c.store import Store
from swda_part2c.orchestrator import Orchestrator, scenarios
from swda_part2c.evaluation import evaluate
from swda_part2c.analysis import canonical

@pytest.fixture
def store(tmp_path):return Store(tmp_path/'boundary.db')

def rec(r,k):return [x['data'] for x in r['records'] if x['kind']==k]

@pytest.mark.parametrize('cap,status',[(4,'BLOCKED'),(5,'COMPLETE')])
def test_exact_test_call_boundary(store,cap,status):
    r=Orchestrator(store,Limits(test_calls=cap)).execute(scenarios()['two_actor'],'TEST')
    assert r['run']['status']==status
    assert next(b['used'] for b in r['budgets'] if b['scope']==r['run']['id'])==cap

@pytest.mark.parametrize('cap,status',[(8,'BLOCKED'),(9,'REVIEW_PENDING')])
def test_exact_lineage_call_boundary(store,cap,status):
    r=Orchestrator(store,Limits(lineage_calls=cap)).execute(scenarios()['two_actor'])
    assert r['run']['status']==status
    assert next(b['used'] for b in r['budgets'] if b['scope']==r['run']['id'])==cap

@pytest.mark.parametrize('cap,status',[(1,'BLOCKED'),(2,'REVIEW_PENDING')])
def test_scheduled_cf_boundary(store,cap,status):
    r=Orchestrator(store,Limits(cf=cap)).execute(scenarios()['two_actor'])
    assert r['run']['status']==status and len(r['children'])==cap

@pytest.mark.parametrize('retries,calls',[(0,1),(2,3)])
def test_exact_schema_retry_boundary(store,retries,calls):
    s=scenarios()['two_actor'].model_copy(update={'fault':'malformed'})
    r=Orchestrator(store,Limits(retries=retries)).execute(s,'TEST')
    assert r['run']['status']=='BLOCKED'
    inv=rec(r,'invocation');assert len(inv)==calls
    assert [i['context']['envelope']['attempt'] for i in inv]==list(range(calls))

@pytest.mark.parametrize('rounds,turns,status',[(4,12,'NO_PATTERN'),(4,11,'BLOCKED')])
def test_round_and_turn_upper_bound(store,rounds,turns,status):
    s=scenarios()['benign_s5'].model_copy(update={'rounds':rounds})
    r=Orchestrator(store,Limits(turns=turns)).execute(s,'TEST')
    assert r['run']['status']==status
    assert len(rec(r,'message'))==turns

@pytest.mark.parametrize('cap,passed',[(40,False),(41,True)])
def test_exact_suite_call_boundary(store,cap,passed):
    r=evaluate(store,Limits(suite_calls=cap))
    assert r['passed']==passed
    b=next(b for b in r['usage'] if b['scope']==r['suite_id'])
    assert b['used']==cap

def test_test_fixture_count(store):
    r=evaluate(store,Limits(test_fixtures=11))
    assert r['executed']==11 and not r['complete'] and not r['passed']

@pytest.mark.parametrize('limits',[{'cards':0},{'cards':4},{'rounds':5},{'turns':13},
    {'retries':3},{'test_fixtures':13},{'seconds':121.0},{'lineage_calls':49}])
def test_invalid_limit_configuration_rejected(limits):
    with pytest.raises(ValueError): Limits(**limits)

def test_timeout_prevents_first_model_call(store):
    r=Orchestrator(store,Limits(seconds=0.000000001)).execute(scenarios()['two_actor'])
    assert r['run']['status']=='BLOCKED' and not rec(r,'invocation')

def test_all_packaged_semantic_traces_reproduce(store):
    for name,s in scenarios().items():
        committed=json.loads((ROOT/'examples'/f'{name}.trace.json').read_text())
        fresh=Orchestrator(store).execute(s)
        assert canonical(committed)==canonical(fresh), name
        old=rec(committed,'card');new=rec(fresh,'card')
        assert len(old)==len(new)
        if old:
            # Check independently beyond the submitted canonical helper.
            for field in ('title','summary','actors','limitations','classification',
                          'comparison_rationale','missing_data','machine_outcome','human_status'):
                assert old[0][field]==new[0][field],(name,field)
            assert [{k:v for k,v in f.items() if k!='trace_ids'} for f in old[0]['flows']]==[
                {k:v for k,v in f.items() if k!='trace_ids'} for f in new[0]['flows']]
            assert [(c['removed_actor'],c['outcome']) for c in old[0]['counterfactuals']]==[
                (c['removed_actor'],c['outcome']) for c in new[0]['counterfactuals']]

def test_every_packaged_evaluation_trace_matches_report():
    report=json.loads((ROOT/'examples/evaluation.json').read_text())
    traces=json.loads((ROOT/'examples/evaluation-traces.json').read_text())
    assert len(traces)==report['executed']==12
    by_id={r['run']['id']:r for r in traces}
    for f in report['results']:
        r=by_id[f['run_id']]
        assert r['run']['kind']=='TEST' and r['run']['parent'] is None
        assert r['run']['status']==f['actual']==f['expected']
        assert len(rec(r,'message'))==f['message_count']
        assert not r['children'] and not r['decisions']
        assert all(check is True for check in f['checks'].values())

def test_all_original_annex_fields_against_assessment():
    expected=[
      ('MO-01','Dormant-entity claim syndicate','Dormant entities act as employers and training providers to submit false grant claims','Observed'),
      ('MO-02','Forged evidence during checks','False records are provided when claims are checked or audited','Observed'),
      ('MO-03','Credit encashment','Individuals submit false claims without attending a course','Observed'),
      ('MO-04','Cash for enrolment','Agents or recruiters offer cash for using credits and suggest attendance is optional','Observed'),
      ('MO-05','Falsified attendance','Attendance is recorded for training that did not take place','Observed'),
      ('MO-06','Employment created for grants','People are hired only to attend a course and are let go afterwards','Observed'),
      ('MO-07','Overclaimed training','Claims exceed the training or attendance actually delivered','Observed overseas'),
      ('MO-08','Indirect kickback through a sponsor','A sponsor pays the nett fee while value flows back through the provider','Policy risk')]
    cat=Catalogue()
    for sid,name,text,basis in expected:
        r=cat.read((sid,))[0];assert (r.name,r.text,r.basis)==(name,text,basis)
    excerpts=[
      'I signed up for a short course, then found out it’s only available as part of a longer diploma. Feels misleading.',
      'Almost $600 for basic cleaning training? How is that worth it?',
      'A marketing agent kept pushing my elderly mum to use her credits and mentioned a cash reward. Not sure what the course even was.',
      'Nobody in my class ever fails. Feels like providers just pass everyone to keep the funding.',
      'Took a practical course last year and it was actually useful.']
    for i,text in enumerate(excerpts,1):
        r=cat.read((f'S{i}',))[0]
        assert r.text==text and r.trust=='EXERCISE_UNVERIFIED'

def test_actor_script_input_sensitivity(store):
    from swda_part2c.schemas import Context
    from swda_part2c.models import adapters
    result=Orchestrator(store).execute(scenarios()['two_actor'],'TEST')
    inv=rec(result,'invocation')
    ta=next(i for i in inv if i['context']['envelope']['actor']=='TA')
    ctx=Context.model_validate_json(json.dumps(ta['context']))
    model=adapters()['TA']
    original=json.loads(model.generate(ctx))
    without=json.loads(model.generate(ctx.model_copy(update={'incoming':()})))
    assert original['contribution']['material'] and not without['contribution']['material']
    seeded=json.loads(model.generate(ctx.model_copy(update={'scenario':ctx.scenario.model_copy(update={'seed':ctx.scenario.seed+1})})))
    assert seeded['claims'][0]!=original['claims'][0]

def test_equal_seed_policy_and_source_versions_for_every_cf(store):
    result=Orchestrator(store).execute(scenarios()['three_role'])
    baseline=rec(result,'snapshots')[0]
    assert len(result['children'])==3
    parent_ids={m['envelope']['message_id'] for m in rec(result,'message')}
    for child in result['children']:
        snap=rec(child,'snapshots')[0]
        assert snap['scenario']==baseline['scenario']
        assert snap['policy']==baseline['policy']
        assert snap['source_manifest']==baseline['source_manifest']
        reset=rec(child,'context_reset')[0]
        assert reset['copied_parent_messages']==[] and reset['fresh_history']
        removed=json.loads(child['run']['metadata'])['removed_actor']
        for i in rec(child,'invocation'):
            ctx=i['context'];assert ctx['envelope']['actor']!=removed
            assert not any(m['envelope']['message_id'] in parent_ids for m in ctx['incoming']+ctx['prior'])
