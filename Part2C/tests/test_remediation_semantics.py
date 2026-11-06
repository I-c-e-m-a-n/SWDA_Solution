"""F1–F4/F10: semantic adversarial cases, including the independent review probes."""
import copy
import json
import pytest
from swda_part2c.schemas import Context, Response
from swda_part2c.orchestrator import Orchestrator, scenarios, profiles
from swda_part2c.models import adapters
from swda_part2c.policy import Gateway, Denied
from swda_part2c.sources import Catalogue
from swda_part2c.grounding import support, contribution_text, benefit_text, relevant_data
from swda_part2c.analysis import dependency_graph


def rows(result, kind):
    return [r['data'] for r in result['records'] if r['kind']==kind]


def change_models(actor, mutate):
    def factory():
        models=adapters(); old=models[actor].generate
        def generate(ctx):
            output=json.loads(old(ctx)); mutate(output,ctx); return json.dumps(output)
        models[actor].generate=generate
        return models
    return factory


def set_contribution(output, ctx, features, parents=()):
    c=output['contribution']; c.update(features=list(features),material=bool(features),
        depends_on=[m.envelope.message_id for m in parents],
        dependency_features={m.envelope.message_id:list(m.response.contribution.features) for m in parents})
    c['claim']['text']=contribution_text(ctx.envelope.actor, features)
    c['benefit']['text']=benefit_text(ctx.envelope.actor, features)


@pytest.mark.parametrize('sources,features,mode',[
    (('S5',),('false_claim','nonattendance'),'single'),
    (('S5',),('cash_offer','credit_use'),'dependency'),
    (('S5','MO-03'),('cash_offer',),'single'),
    (('S1','S2'),('false_claim','nonattendance'),'dependency'),
    (('S1','S2'),('bundling_value_hypothesis','price_value_hypothesis'),'dependency'),
    (('MO-03',),('cash_offer',),'single'),
    (('S3','S4'),('cash_offer','credit_use'),'dependency'),
])
def test_f1_unsupported_mechanism_never_reviewable(store,sources,features,mode):
    sc=scenarios()['single_actor'].model_copy(update={'sources':sources,'features':features,'mode':mode})
    result=Orchestrator(store).execute(sc)
    assert result['run']['status']=='NO_PATTERN'
    assert not rows(result,'card') and not rows(result,'invocation')
    evidence=rows(result,'grounding')[0]
    assert evidence['unsupported'] and set(evidence['features'])==set(features)


def test_f1_registry_distinguishes_direct_context_benign_and_unsupported():
    evidence=support(('cash_offer','credit_use','optional_attendance','false_claim'),('MO-04','S3','S5'))
    assert evidence['features']['cash_offer']=={'direct':['MO-04'],'context':['S3'],'level':'DIRECT_CONCEPT'}
    assert evidence['features']['false_claim']['level']=='UNSUPPORTED'
    assert evidence['benign']==['S5'] and not evidence['eligible']
    assert support(('bundling_value_hypothesis',),('S1',))['features']['bundling_value_hypothesis']['level']=='WEAK_CONTEXT'


def test_f1_unrelated_existing_source_on_actor_claim_is_denied(store,sc):
    def mutate(out,ctx):
        out['contribution']['claim']['source_ids']=['S3']  # context cannot support optional attendance
    result=Orchestrator(store,model_factory=change_models('PA',mutate)).execute(sc)
    assert result['run']['status']=='BLOCKED' and not rows(result,'message')
    assert any(p['code']=='UNSUPPORTED_FEATURE_SOURCE' for p in rows(result,'policy'))


@pytest.mark.parametrize('name',['two_actor','three_role','single_actor','variation'])
def test_f1_valid_mo_supported_hypotheses_survive(store,name):
    assert Orchestrator(store).execute(scenarios()[name])['run']['status']=='REVIEW_PENDING'


def independent_factory():
    models=adapters()
    for actor in ('TA','PA','EA'):
        old=models[actor].generate
        def generate(ctx,old=old):
            out=json.loads(old(ctx)); pos=ctx.scenario.roles.index(ctx.envelope.actor)
            set_contribution(out,ctx,ctx.scenario.features[pos::len(ctx.scenario.roles)])
            return json.dumps(out)
        models[actor].generate=generate
    return models


def test_f2_disjoint_partitions_are_not_cooperation(store,sc):
    result=Orchestrator(store,model_factory=independent_factory).execute(sc)
    assert result['run']['status']=='BLOCKED'
    assert len(rows(result,'counterfactual'))==2
    assert all(c['outcome']=='INCONCLUSIVE' for c in rows(result,'counterfactual'))
    assert any(g['name']=='counterfactual_evidence' and not g['passed'] for g in rows(result,'gate'))


@pytest.mark.parametrize('name,count',[('two_actor',2),('three_role',3)])
def test_f2_positive_material_cooperation_and_fresh_cf(store,name,count):
    result=Orchestrator(store).execute(scenarios()[name]); assert result['run']['status']=='REVIEW_PENDING'
    assert len(rows(result,'counterfactual'))==count
    for cf in result['children']:
        removed=json.loads(cf['run']['metadata'])['removed_actor']
        assert all(i['context']['envelope']['actor']!=removed for i in rows(cf,'invocation'))
        assert rows(cf,'context_reset')[0]['copied_parent_messages']==[]
        assert all(c['outcome']=='MULTI_PARTY_DEPENDENCY' for c in rows(result,'counterfactual'))


def test_f2_nonessential_actor_leaves_a_smaller_coalition(store):
    sc=scenarios()['three_role'].model_copy(update={'roles':('PA','TA','EA'),'rounds':1})
    def factory():
        models=adapters()
        for actor in ('PA','TA','EA'):
            old=models[actor].generate
            def generate(ctx,old=old):
                out=json.loads(old(ctx)); actor=ctx.envelope.actor
                features={'PA':('sponsor_fee','employment_link'),'TA':('provider_return',),'EA':('employment_link',)}[actor]
                parents=tuple(m for m in ctx.incoming if m.response.contribution.material
                              and (actor!='EA' or m.envelope.actor=='TA'))[-1:]
                set_contribution(out,ctx,features if actor=='PA' or parents else (), parents)
                return json.dumps(out)
            models[actor].generate=generate
        return models
    result=Orchestrator(store,model_factory=factory).execute(sc)
    assert result['run']['status']=='REVIEW_PENDING'
    cf=next(c for c in rows(result,'counterfactual') if c['removed_actor']=='EA')
    assert cf['outcome']=='SURVIVING_COALITION' and set(cf['surviving_actors'])=={'PA','TA'}
    assert not any(c['outcome']=='SINGLE_ACTOR_FEASIBILITY' for c in rows(result,'counterfactual'))
    assert 'SMALLER_COALITION_SURVIVES' in rows(result,'recommendation')[0]['findings']


@pytest.mark.parametrize('attack',['fabricated','self','future','unrelated_features','nonmaterial','duplicate'])
def test_f2_invalid_dependency_rejected(store,sc,attack):
    def mutate(out,ctx):
        c=out['contribution']; parent=ctx.incoming[-1].envelope.message_id
        if attack in ('fabricated','self','future'):
            target={'fabricated':'unseen','self':ctx.envelope.message_id,'future':'future-message'}[attack]
            c['depends_on']=[target]; c['dependency_features']={target:['cash_offer']}
        elif attack=='unrelated_features': c['dependency_features']={parent:['false_claim']}
        elif attack=='nonmaterial': c['material']=False
        else: c['depends_on']=[parent,parent]
    result=Orchestrator(store,model_factory=change_models('TA',mutate)).execute(sc)
    assert result['run']['status']=='BLOCKED'
    assert not any(m['envelope']['actor']=='TA' for m in rows(result,'message'))


def test_f2_nonmaterial_incoming_does_not_unlock_contribution(candidate):
    ctx=Context.model_validate_json(json.dumps(next(i for i in rows(candidate,'invocation') if i['context']['envelope']['actor']=='TA')['context']))
    parents=tuple(m.model_copy(update={'response':m.response.model_copy(update={
        'contribution':m.response.contribution.model_copy(update={'material':False})})}) for m in ctx.incoming)
    out=json.loads(adapters()['TA'].generate(ctx.model_copy(update={'incoming':parents})))
    assert not out['contribution']['material'] and not out['contribution']['depends_on']


def reviewer_context(candidate):
    return Context.model_validate_json(json.dumps(next(i for i in rows(candidate,'invocation') if i['context']['envelope']['actor']=='REV')['context']))


@pytest.mark.parametrize('mutation,expected',[
    ('unknown','MISSING_OR_UNAUTHORISED_REFERENCES'), ('factual','CHALLENGED_ASSERTIONS'),
    ('missing','MISSING_OR_UNAUTHORISED_REFERENCES'), ('assumptions','MISSING_MATERIAL_ASSUMPTIONS'),
    ('uncertainty','MISSING_UNCERTAINTY'), ('actors','ACTOR_PARTICIPATION_MISMATCH'),
    ('counterfactual','REVIEW_ABSTAINS'), ('comparison','COMPARATOR_EVIDENCE_MISMATCH'),
])
def test_f3_reviewer_changes_with_material_draft_defects(candidate,mutation,expected):
    ctx=reviewer_context(candidate); original=json.loads(adapters()['REV'].generate(ctx))
    draft=copy.deepcopy(ctx.draft); updates={'draft':draft}
    if mutation=='unknown': draft['sources']=['S99']
    elif mutation=='factual': draft['contributions'][0]['claim']['text']='Actual misconduct is proven by these records.'
    elif mutation=='missing': updates['references']=()
    elif mutation=='assumptions': draft['assumptions']=[]
    elif mutation=='uncertainty': draft['limitations']=[]
    elif mutation=='actors': draft['actors']=['EA']
    elif mutation=='counterfactual': draft['cf'][0]['outcome']='INCONCLUSIVE'
    elif mutation=='comparison': updates['comparison']=dict(ctx.comparison,classification='NEW')
    altered=json.loads(adapters()['REV'].generate(ctx.model_copy(update=updates)))
    assert altered!=original and altered['abstained'] and expected in altered['findings']


def test_f3_benign_counter_signal_is_visible_and_not_fraud_evidence(store,sc):
    result=Orchestrator(store).execute(sc.model_copy(update={'sources':sc.sources+('S5',)}))
    recommendation=rows(result,'recommendation')[0]
    assert recommendation['benign_signals']==['S5']
    assert 'BENIGN_COUNTERSIGNAL_REQUIRES_CAUTION' in recommendation['findings']
    assert result['run']['status']=='REVIEW_PENDING'  # directly supported MO remains a hypothesis


@pytest.mark.parametrize('attack',['approve','classification','findings','rationale'])
def test_f3_reviewer_has_no_gate_or_approval_authority(store,sc,attack):
    def mutate(out,ctx):
        if attack=='approve': out['operation']='APPROVE_FOR_INVESTIGATION'
        elif attack=='classification': out['classification']='NEW'
        elif attack=='findings': out['findings']=[]
        else: out['rationale']='Actual misconduct has been conclusively verified.'
    result=Orchestrator(store,model_factory=change_models('REV',mutate)).execute(sc)
    assert result['run']['status']=='BLOCKED' and not result['decisions']


@pytest.mark.parametrize('data',[[],[''],['Independently verified employment records'],['Internet search'],
    ['Independently verified attendance records','Independently verified attendance records']])
def test_f4_empty_irrelevant_duplicate_requirements_block(store,sc,data):
    result=Orchestrator(store,model_factory=change_models('REV',lambda out,ctx:out.update(missing_data=data))).execute(sc)
    assert result['run']['status']=='BLOCKED'
    assert any(g['name']=='reviewer_validity' and not g['passed'] for g in rows(result,'gate'))


def test_f4_relevant_data_and_benign_abstention(store,sc):
    result=Orchestrator(store).execute(sc)
    assert tuple(rows(result,'card')[0]['missing_data'])==relevant_data(sc.features)
    benign=Orchestrator(store).execute(scenarios()['benign_s5'])
    assert benign['run']['status']=='NO_PATTERN' and not rows(benign,'recommendation')


def test_f10_cards_have_distinct_supported_mechanisms_and_trace_linked_flows(store):
    cards={}
    for name in ('two_actor','three_role','single_actor','variation'):
        result=Orchestrator(store).execute(scenarios()[name]); card=rows(result,'card')[0]; cards[name]=card
        ids={m['envelope']['message_id'] for m in rows(result,'message')}
        assert all(set(f['trace_ids'])<=ids for f in card['flows'])
        assert all(c['features'] and 'modelling assumption' in c['claim']['text'] for c in card['contributions'])
        assert 'shared=' in card['comparison_rationale'] and 'absent=' in card['comparison_rationale']
        assert all(f['source_actor']=='SCHEME' or f['source_actor'] in card['actors'] for f in card['flows'])
        assert all(f['destination_actor'] in card['actors'] for f in card['flows'])
    assert len({c['summary']['text'] for c in cards.values()})==4
    assert 'cash inducement' in cards['two_actor']['summary']['text']
    assert 'sponsor fee support' in cards['three_role']['summary']['text']
    assert 'nonattendance' in cards['single_actor']['summary']['text']
    assert not any(f['flow_type']=='contribution_dependency' for f in cards['single_actor']['flows'])
    assert 'optional_attendance' in cards['variation']['comparison_rationale']
    new=Orchestrator(store).execute(scenarios()['new_relative'])
    assert new['run']['status']=='NO_PATTERN' and not rows(new,'card')


def test_f2_earlier_cooperation_does_not_hide_independent_final_contributions(store,sc):
    def factory():
        models=adapters()
        for actor in ('PA','TA'):
            old=models[actor].generate
            def generate(ctx,old=old):
                out=json.loads(old(ctx))
                if ctx.envelope.round==2:
                    pos=ctx.scenario.roles.index(ctx.envelope.actor)
                    set_contribution(out,ctx,ctx.scenario.features[pos::len(ctx.scenario.roles)])
                return json.dumps(out)
            models[actor].generate=generate
        return models
    result=Orchestrator(store,model_factory=factory).execute(sc)
    assert result['run']['status']=='BLOCKED'
    assert all(c['outcome']=='INCONCLUSIVE' for c in rows(result,'counterfactual'))
