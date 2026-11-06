"""Pure deterministic reviewer rules; no catalogue, gateway, store or approval handle.

The safety gate rebuilds its own draft and applies these rules to trusted inputs;
a model's claimed checks cannot grant eligibility.
"""
from pydantic import ValidationError
from .schemas import Claim, Contribution, Recommendation
from .grounding import support, relevant_data, contribution_text, benefit_text
from .policy import ASSUMPTION

LIMITATIONS = ('Illustrative MO similarity is separate from weak evidential confidence.',
               'Exercise excerpts are unverified; simulation establishes no misconduct.',
               'Counterfactuals test scripted dependencies, not real-world causation.')


def review(context):
    from .analysis import compare
    draft = context.draft or {}
    refs = {r.source_id: r for r in context.references}
    sources = draft.get('sources', [])
    findings, challenged, missing, unsupported, objections = set(), set(), set(), set(), set()
    missing.update(set(sources) - set(refs))
    if set(sources) != set(context.scenario.sources):
        findings.add('DRAFT_SOURCE_SCOPE_MISMATCH')
    grounding = support(draft.get('features', ()), set(sources) & set(refs))
    unsupported.update(grounding['unsupported'])
    if set(draft.get('features', ())) != set(context.scenario.features):
        findings.add('FEATURE_SET_MISMATCH')
    cs = []
    for i, value in enumerate(draft.get('contributions', [])):
        try:
            c = Contribution.model_validate_json(__import__('json').dumps(value))
        except (ValidationError, TypeError):
            challenged.add(f'contribution:{i}:INVALID_CONTRACT')
            continue
        cs.append(c)
        if not c.material or not c.features:
            challenged.add(f'contribution:{i}:NONMATERIAL')
        for claim in (c.claim, c.benefit):
            missing.update(set(claim.source_ids) - set(refs))
            unsupported.update(support(c.features, set(claim.source_ids) & set(refs))['unsupported'])
        if c.claim.label != 'SIMULATION' or c.claim.text != contribution_text(c.actor, c.features):
            challenged.add(f'contribution:{i}:UNSUPPORTED_ASSERTION')
        if c.benefit.label != 'SIMULATION' or c.benefit.text != benefit_text(c.actor, c.features):
            challenged.add(f'contribution:{i}:UNSUPPORTED_BENEFIT')
    if not cs or set(draft.get('actors', [])) != {c.actor for c in cs} or len(cs) != len({c.actor for c in cs}):
        findings.add('ACTOR_PARTICIPATION_MISMATCH')
    if {f for c in cs for f in c.features} != set(draft.get('features', [])):
        findings.add('CONTRIBUTION_FEATURE_MISMATCH')
    assertions = draft.get('assertions', [])
    if not assertions:
        findings.add('MISSING_PROVENANCE')
    for i, value in enumerate(assertions):
        try:
            claim = Claim.model_validate_json(__import__('json').dumps(value))
        except (ValidationError, TypeError):
            challenged.add(f'assertion:{i}:INVALID_CONTRACT')
            continue
        missing.update(set(claim.source_ids) - set(refs))
        if claim.label == 'SOURCE':
            if len(claim.source_ids) != 1 or claim.source_ids[0] not in refs or claim.text != refs[claim.source_ids[0]].text:
                challenged.add(f'assertion:{i}:INACCURATE_QUOTATION')
        elif claim.label != 'ASSUMPTION' or claim.text != ASSUMPTION:
            challenged.add(f'assertion:{i}:UNSUPPORTED_FACTUAL_ASSERTION')
    if ASSUMPTION not in draft.get('assumptions', []):
        findings.add('MISSING_MATERIAL_ASSUMPTIONS')
    if not draft.get('limitations') or not any('causation' in x for x in draft['limitations']):
        findings.add('MISSING_UNCERTAINTY')
    graph = draft.get('graph', {})
    if graph.get('errors') or not (graph.get('single') or graph.get('cooperative')):
        findings.add('UNSUBSTANTIATED_COOPERATION')
    if context.envelope.run_type == 'CANDIDATE':
        cfs = draft.get('cf', [])
        if len(cfs) != len(cs) or {c.get('removed_actor') for c in cfs} != {c.actor for c in cs}:
            objections.add('INCOMPLETE_ACTOR_REMOVALS')
        for cf in cfs:
            if cf.get('outcome') == 'INCONCLUSIVE':
                objections.add('INCONCLUSIVE_REMOVAL:' + str(cf.get('removed_actor')))
            if cf.get('outcome') == 'SURVIVING_COALITION':
                findings.add('SMALLER_COALITION_SURVIVES')
    benign = sorted(k for k in sources if k in refs and refs[k].benign)
    if benign:
        findings.add('BENIGN_COUNTERSIGNAL_REQUIRES_CAUTION')
    if missing:
        findings.add('MISSING_OR_UNAUTHORISED_REFERENCES')
    if unsupported:
        findings.add('UNSUPPORTED_RISK_FEATURES')
    if challenged:
        findings.add('CHALLENGED_ASSERTIONS')
    try:
        independent = compare({f for c in cs for f in c.features}, context.references)
    except ValueError:
        independent = {'classification': 'INCONCLUSIVE', 'matches': [], 'rationale': ''}
        findings.add('MISSING_COMPARISON_REFERENCES')
    comparator = context.comparison or {}
    if any(comparator.get(k) != independent[k] for k in ('classification', 'matches', 'rationale')):
        findings.add('COMPARATOR_EVIDENCE_MISMATCH')
    blocking = findings - {'BENIGN_COUNTERSIGNAL_REQUIRES_CAUTION', 'SMALLER_COALITION_SURVIVES'}
    abstain = bool(blocking or objections or not grounding['eligible'])
    findings.add('REVIEW_ABSTAINS' if abstain else 'HYPOTHETICAL_CONCEPTS_SUPPORTED')
    return Recommendation(classification='INCONCLUSIVE' if abstain else independent['classification'],
        matches=tuple(independent['matches']),
        rationale='Review abstains: resolve challenged evidence before investigation review.' if abstain else
                  'Review supports an illustrative concept comparison; contributions, assumptions and empirical gaps remain hypothetical.',
        limitations=LIMITATIONS, missing_data=relevant_data(draft.get('features', ())),
        findings=tuple(sorted(findings)), challenged_assertions=tuple(sorted(challenged)),
        missing_references=tuple(sorted(missing)), unsupported_features=tuple(sorted(unsupported)),
        counterfactual_objections=tuple(sorted(objections)), benign_signals=tuple(benign), abstained=abstain)
