"""Independent application gates. Models cannot set these outcomes."""
import json
from .schemas import Card, Message, Recommendation, Context
from .release import EXPECTED, TEST_EXPECTED
from .approval import REQUIRED_GATES
from .grounding import support, valid_data
from .analysis import make_draft, dependency_graph, cf_outcome
from .review import review


def assess(run, card, messages, catalogue, store, evaluation, recommendation, comparison):
    Card.model_validate_json(card.model_dump_json())
    for m in messages:
        Message.model_validate_json(m.model_dump_json())
    Recommendation.model_validate_json(recommendation.model_dump_json())
    records = store.records(run.run_id)
    policies = [r['data'] for r in records if r['kind'] == 'policy']
    allowed = all(p['allowed'] for p in policies)
    references = {r.source_id:r for r in catalogue.read(run.scenario.sources)}
    assertions = (*card.assertions, card.summary, *(f.claim for f in card.flows),
                  *(c.claim for c in card.contributions), *(c.benefit for c in card.contributions))
    attributed = all(c.source_ids and set(c.source_ids) <= set(references) for c in assertions)
    grounded = support(run.scenario.features, references)['eligible'] and all(
        support(c.features, c.claim.source_ids)['eligible'] and support(c.features, c.benefit.source_ids)['eligible']
        for c in card.contributions)
    quotes = all(c.label != 'SOURCE' or (len(c.source_ids) == 1 and c.text == references[c.source_ids[0]].text)
                 for c in assertions)
    graph = dependency_graph(messages, run.scenario)
    cf_valid = (len(card.counterfactuals) == len(card.actors)
                and {c.removed_actor for c in card.counterfactuals} == set(card.actors))
    for c in card.counterfactuals:
        if not c.run_id or c.outcome == 'INCONCLUSIVE':
            cf_valid = False
            continue
        child = store.run(c.run_id)
        reduced = [Message.model_validate_json(json.dumps(r['data'])) for r in store.records(c.run_id, 'message')]
        cf_valid &= (c.parent_run_id == run.run_id and child['parent'] == run.run_id
                     and child['kind'] == 'CF' and child['status'] == 'COMPLETE'
                     and json.loads(child['metadata'])['removed_actor'] == c.removed_actor
                     and c.outcome == cf_outcome(messages, reduced, run.scenario, True, c.removed_actor))
    dependencies = (graph['single'] or graph['cooperative']) and (run.run_type == 'TEST' or cf_valid)
    expected = EXPECTED | TEST_EXPECTED
    integrity = all(expected.get(k) == v for k,v in catalogue.manifest.items() if k != 'manifest_version')
    safe = quotes and len([p for p in policies if p['stage'] == 'safety' and p['allowed']]) == len(messages)
    # Rebuild the draft from trusted transcript and source records. Do not trust the
    # adapter's findings, even if its schema and comparator classification are valid.
    inv = next(r['data'] for r in reversed(records) if r['kind'] == 'invocation'
               and r['data']['context']['envelope']['actor'] == 'REV')
    ctx = Context.model_validate_json(json.dumps(inv['context']))
    trusted = ctx.model_copy(update={'draft':make_draft(run, messages, card.counterfactuals),
        'references':catalogue.read(ctx.envelope.source_ids), 'comparison':comparison})
    expected_review = review(trusted)
    fields = ('classification', 'matches', 'findings', 'challenged_assertions', 'missing_references',
              'unsupported_features', 'counterfactual_objections', 'benign_signals', 'abstained', 'limitations')
    reviewer = (not expected_review.abstained and not recommendation.abstained
                and all(getattr(recommendation, k) == getattr(expected_review, k) for k in fields)
                and recommendation.rationale == expected_review.rationale
                and valid_data(recommendation.missing_data, run.scenario.features)
                and card.missing_data == recommendation.missing_data
                and card.classification == comparison['classification'])
    starts = [r['data']['invocation_id'] for r in records if r['kind'] == 'invocation_started']
    ends = [r['data']['invocation_id'] for r in records if r['kind'] == 'invocation']
    bounded = (all(b['used'] <= b['cap'] for b in store.usage()) and len(messages) <= 12
               and len(card.actors) <= 3 and sorted(starts) == sorted(ends) and len(starts) == len(set(starts)))
    gates = dict(source_integrity=integrity, schema_validity=True,
        source_reference_allowlisting=attributed, assertion_provenance=attributed and grounded,
        policy_compliance=allowed, bounded_execution=bounded, output_safety=safe,
        counterfactual_evidence=dependencies, reviewer_validity=reviewer,
        required_evaluation=evaluation.passed,
        human_review_eligibility=run.run_type == 'CANDIDATE' and dependencies and grounded and reviewer)
    assert set(gates) == REQUIRED_GATES
    return gates
