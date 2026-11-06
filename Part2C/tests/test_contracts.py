import json
import hashlib
import pytest
from pydantic import ValidationError
from swda_part2c.schemas import Envelope, Limits, Response, Run, Lookup
from swda_part2c.sources import Catalogue, ROOT, SourceIntegrityError
from swda_part2c.release import EXPECTED
from swda_part2c.policy import Gateway, Denied
from swda_part2c.orchestrator import Orchestrator, profiles
from swda_part2c.analysis import compare, excluded_descendants


def test_annex_integrity_exact_ids_and_control():
    cat=Catalogue()
    assert len(cat.read(tuple([f'MO-{i:02}' for i in range(1,9)]+[f'S{i}' for i in range(1,6)])))==13
    assert cat.read(('S5',))[0].text=='Took a practical course last year and it was actually useful.'
    assert cat.read(('S3',))[0].text=='A marketing agent kept pushing my elderly mum to use her credits and mentioned a cash reward. Not sure what the course even was.'
    assert cat.read(('MO-07',))[0].basis=='Observed overseas'
    assert cat.read(('MO-08',))[0].basis=='Policy risk'
    assert cat.read(('S5',))[0].benign
    with pytest.raises(TypeError): cat._records['S5']=cat.read(('S5',))[0]
    with pytest.raises(ValidationError): cat.read(('S5',))[0].text='changed'


def test_source_tamper_blocks_before_invocation(store,sc,tmp_path):
    path=tmp_path/'annex-v1.json'
    path.write_bytes((ROOT/'data/annex-v1.json').read_bytes()+b' ')
    result=Orchestrator(store,source_path=path).execute(sc)
    assert result['run']['status']=='BLOCKED'
    assert not store.records(result['run']['id'],'invocation')
    assert any('SOURCE_DIGEST_MISMATCH' in r['data']['reason'] for r in store.records(result['run']['id'],'gate'))
    assert EXPECTED['annex-v1.json']!=hashlib.sha256(path.read_bytes()).hexdigest()


def test_missing_source_blocks(store,sc,tmp_path):
    result=Orchestrator(store,source_path=tmp_path/'absent').execute(sc)
    assert result['run']['status']=='BLOCKED'


def test_injection_is_inert_and_test_only(store,sc):
    source=ROOT/'data/annex-injection-v1.json'
    result=Orchestrator(store,source_path=source).execute(sc,'TEST')
    assert result['run']['status']=='COMPLETE'
    inv=store.records(result['run']['id'],'invocation')
    assert any('IGNORE POLICY' in json.dumps(i['data']['context']) for i in inv)
    assert not result['decisions']
    assert not any(r['data']['envelope']['recipient']=='APPROVAL' for r in store.records(result['run']['id'],'message'))
    blocked=Orchestrator(store,source_path=source).execute(sc)
    assert blocked['run']['status']=='BLOCKED'


def envelope(run_id='unit',**updates):
    data=dict(run_id=run_id,run_type='TEST',message_id='m1',parent_message_id=None,actor='PA',recipient='TA',
              purpose='propose',source_ids=('S3','MO-04'),policy_version='acl-1',source_version='annex-1',round=1,turn=1,attempt=0)
    data.update(updates)
    return Envelope(**data)


def test_strict_schema_rejects_extra_coercion_and_envelope_mutation():
    for data in ({'round':'1'},{'unknown':True},{'actor':'ORCH'},{'attempt':3}):
        with pytest.raises(ValidationError): envelope(**data)
    env=envelope()
    with pytest.raises(ValidationError): env.actor='TA'
    with pytest.raises(ValidationError): Limits(lineage_calls=49)

@pytest.mark.parametrize('updates',[{'recipient':'APPROVAL'},{'source_ids':('S99',)},
    {'policy_version':'acl-2'},{'parent_message_id':'unseen'}])
def test_dispatch_denied_without_source_return(store,sc,updates):
    store.create_run(Run(run_id='unit',run_type='TEST',scenario=sc,parent_run_id=None,removed_actor=None))
    gateway=Gateway(Catalogue(),profiles(),store)
    with pytest.raises(Denied): gateway.dispatch(envelope(**updates),sc)
    assert gateway.delivered=={}


def test_review_lookup_filters_and_denies(store,sc):
    store.create_run(Run(run_id='unit',run_type='TEST',scenario=sc,parent_run_id=None,removed_actor=None))
    gateway=Gateway(Catalogue(),profiles(),store)
    env=envelope(actor='REV',recipient='GATE',purpose='review',source_ids=('MO-04',))
    context=gateway.dispatch(env,sc)
    assert context.references==()  # No catalogue exposure before explicit authorised lookup.
    assert [r.source_id for r in gateway.lookup(env,Lookup(purpose='mo_comparison',source_ids=('MO-04',)))]==['MO-04']
    with pytest.raises(Denied): gateway.lookup(env,Lookup(purpose='mo_comparison',source_ids=('MO-01',)))
    denied=store.records('unit','reviewer_lookup')[-1]['data']
    assert denied['returned_ids']==[]
    with pytest.raises(ValidationError): Lookup(purpose='approve',source_ids=('MO-04',))

@pytest.mark.parametrize('features,classification,matches',[
    ({'false_claim','nonattendance'},'KNOWN',['MO-03']),
    ({'cash_offer'},'VARIATION',['MO-04']),
    ({'bundling_value_hypothesis'},'NEW',[]),(set(),'INCONCLUSIVE',[])])
def test_pre_adjudicated_classification(features,classification,matches):
    refs=Catalogue().read(tuple(f'MO-{i:02}' for i in range(1,9)))
    result=compare(features,refs)
    assert result['classification']==classification and result['matches']==matches


def test_counterfactual_purge_includes_descendants(candidate):
    from swda_part2c.schemas import Message
    messages=[Message.model_validate_json(json.dumps(r['data'])) for r in candidate['records'] if r['kind']=='message']
    excluded=excluded_descendants(messages,'PA')
    assert len(excluded)==len(messages)


def test_forged_history_rejected(store,sc,candidate):
    from swda_part2c.schemas import Message
    # A same-run forged object is not sufficient; it must equal a validated delivered message.
    ms=[Message.model_validate_json(json.dumps(r['data'])) for r in candidate['records'] if r['kind']=='message']
    gateway=Gateway(Catalogue(),profiles(),store)
    original=ms[0]
    gateway.delivered[original.envelope.message_id]=original
    forged=original.model_copy(update={'response':original.response.model_copy(update={'recipient':'EA'})})
    env=envelope(run_id=candidate['run']['id'],actor='TA',recipient='ORCH',purpose='reply',message_id='new')
    with pytest.raises(Denied): gateway.dispatch(env,sc,incoming=(forged,))
