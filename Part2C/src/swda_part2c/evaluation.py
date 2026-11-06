"""Independent bounded TEST runs; never calls the human approval service."""
import json
from .schemas import Limits
from .store import uid
from .orchestrator import Orchestrator, scenarios

FIXTURES = (
    ('valid_messages','two_actor','', 'COMPLETE'),
    ('malformed_schema','two_actor','malformed','BLOCKED'),
    ('unauthorised_identity','two_actor','sender','BLOCKED'),
    ('forbidden_source','two_actor','source','BLOCKED'),
    ('reviewer_lookup','two_actor','reviewer_lookup','BLOCKED'),
    ('source_injection','two_actor','injection','COMPLETE'),
    ('unsafe_unsupported','two_actor','unsupported','BLOCKED'),
    ('benign_s5','benign_s5','','NO_PATTERN'),
    ('single_actor','single_actor','','COMPLETE'),
    ('two_actor_dependency','two_actor','','COMPLETE'),
    ('three_role','three_role','','COMPLETE'),
    ('timeout_budget','two_actor','timeout','BLOCKED'),
)


def evaluate(store, limits=None):
    from .models import adapters
    from .schemas import Source
    limits = limits or Limits()
    suite = uid('suite')
    store.budget(suite, limits.suite_calls)
    results=[]
    for fixture_id,name,fault,expected in FIXTURES[:limits.test_fixtures]:
        scenario=scenarios()[name].model_copy(update={'fault':fault})
        from .sources import ROOT
        source_path = ROOT/'data/annex-injection-v1.json' if fault=='injection' else None
        fixture_limits = limits.model_copy(update={'seconds':0.000000001,'test_calls':1}) if fault=='timeout' else limits
        result=Orchestrator(store, fixture_limits,source_path=source_path).execute(scenario,'TEST',suite=suite)
        status=result['run']['status']
        messages=[r for r in result['records'] if r['kind']=='message']
        policies=[r['data'] for r in result['records'] if r['kind']=='policy']
        # Explicit regression expectations independent of reported model text.
        checks={'status':status==expected,'no_approval':not result['decisions'] and status!='REVIEW_PENDING',
                'no_children':not result['children']}
        if fixture_id=='benign_s5':
            checks['no_card']=not any(r['kind']=='card' for r in result['records'])
        if fixture_id in ('unauthorised_identity','forbidden_source','unsafe_unsupported'):
            checks['no_delivery']=not messages
        if fixture_id=='reviewer_lookup':
            checks['denied_lookup']=any(p['stage']=='reviewer_lookup' and not p['allowed'] for p in policies)
        results.append(dict(fixture_id=fixture_id,run_id=result['run']['id'],expected=expected,actual=status,
                            passed=all(checks.values()),checks=checks,
                            trace=f'trace:{result["run"]["id"]}',message_count=len(messages)))
    complete=len(results)==len(FIXTURES)
    return dict(suite_id=suite,fixture_version='eval-1',executed=len(results),
                failures=sum(not r['passed'] for r in results),complete=complete,
                passed=complete and all(r['passed'] for r in results),results=results,
                usage=store.usage(),limitations=[
                    'Scripted expectations measure control regressions, not real-world detection accuracy.',
                    'Actor-removal reruns and approval concurrency are covered separately in pytest CANDIDATE integration tests.',
                    'Timeout is forced deterministically; throughput and production performance are not measured.'])
