"""Trusted concept comparison, material dependency analysis and semantic replay."""
import copy
import hashlib
import json
from .schemas import Claim, Card, Evaluation, Flow
from .policy import ASSUMPTION
from .grounding import SIGNATURES, support, describe
from .store import uid


def compare(features, references):
    permitted = {r.source_id for r in references}
    if not set(SIGNATURES) <= permitted:
        raise ValueError('COMPARATOR_REFERENCE_INCOMPLETE')
    features = set(features)
    exact = [k for k, v in SIGNATURES.items() if v == features]
    overlap = [k for k, v in SIGNATURES.items() if v & features]
    kind = 'KNOWN' if exact else 'VARIATION' if overlap else 'NEW' if features else 'INCONCLUSIVE'
    details = [{ 'mo': k, 'shared': sorted(features & SIGNATURES[k]),
                 'absent_from_pattern': sorted(SIGNATURES[k] - features),
                 'additional_to_mo': sorted(features - SIGNATURES[k])} for k in exact or overlap]
    rationale = f'{kind} relative only to MO-01–MO-08. '
    rationale += '; '.join(f"{d['mo']}: shared={d['shared']}, absent={d['absent_from_pattern']}, additional={d['additional_to_mo']}" for d in details)
    rationale += ' Feature similarity describes illustrative concepts, not actual wrongdoing or real-world novelty.'
    return dict(classification=kind, matches=exact or overlap, rationale=rationale, details=details)


def contributions(messages):
    found = {}
    for m in messages:
        if m.response.contribution.material:
            found[m.envelope.actor] = m.response.contribution
    return tuple(found.values())


def structure(messages, scenario):
    """Feature coverage only. Dependency evidence is a separate predicate below."""
    cs = contributions(messages)
    present = {f for c in cs for f in c.features}
    return bool(scenario.features) and set(scenario.features) <= present, cs


def dependency_graph(messages, scenario):
    """Validate a directed acyclic graph using actual earlier routed material messages.

    A required feature set explicitly names the prior contribution being consumed.
    A downstream contribution must add a distinct supported concept. Chronology or
    envelope parentage alone supplies no dependency edge.
    """
    seen, edges, errors = {}, [], []
    for m in messages:
        e, c = m.envelope, m.response.contribution
        if e.message_id in seen:
            errors.append('DUPLICATE_MESSAGE')
        if set(c.depends_on) != set(c.dependency_features):
            errors.append('DEPENDENCY_REQUIREMENTS_MISMATCH')
        for mid in c.depends_on:
            p = seen.get(mid)
            if not p:
                errors.append('DEPENDENCY_NOT_EARLIER')
                continue
            pc, pe = p.response.contribution, p.envelope
            required = c.dependency_features.get(mid, ())
            if not (pe.run_id == e.run_id and pe.recipient == e.actor and pe.actor != e.actor
                    and pe.turn < e.turn and pc.material and c.material and required
                    and set(required) <= set(pc.features) and set(c.features) - set(pc.features)
                    and support(pc.features, pc.claim.source_ids)['eligible']
                    and support(c.features, c.claim.source_ids)['eligible']):
                errors.append('INVALID_MATERIAL_EDGE')
                continue
            edges.append({'source': pe.actor, 'destination': e.actor, 'parent': mid,
                          'child': e.message_id, 'required_features': list(required)})
        seen[e.message_id] = m
    complete, cs = structure(messages, scenario)
    # Only dependencies supporting the selected final material contributions count.
    # An earlier cooperative exchange cannot legitimise later independent outputs.
    latest = {m.envelope.actor:m.envelope.message_id for m in messages if m.response.contribution.material}
    relevant = set(latest.values())
    while True:
        before = len(relevant)
        relevant.update(edge['parent'] for edge in edges if edge['child'] in relevant)
        if len(relevant) == before:
            break
    edges = [edge for edge in edges if edge['child'] in relevant]
    actors = {c.actor for c in cs}
    connected = set()
    if actors:
        connected.add(sorted(actors)[0])
        while True:
            before = len(connected)
            for edge in edges:
                if edge['source'] in connected or edge['destination'] in connected:
                    connected.update((edge['source'], edge['destination']))
            if len(connected) == before:
                break
    return {'coverage': complete, 'actors': sorted(actors), 'edges': edges, 'errors': errors,
            'cooperative': complete and len(actors) >= 2 and bool(edges) and not errors and connected == actors,
            'single': complete and len(actors) == 1 and not edges and not errors}


def cf_outcome(parent_messages, reduced_messages, scenario, complete, removed):
    original = dependency_graph(parent_messages, scenario)
    reduced = dependency_graph(reduced_messages, scenario)
    if not complete or original['errors'] or reduced['errors']:
        return 'INCONCLUSIVE'
    if original['single'] or reduced['single']:
        return 'SINGLE_ACTOR_FEASIBILITY'
    if not original['cooperative']:
        return 'INCONCLUSIVE'
    if reduced['cooperative']:
        return 'SURVIVING_COALITION'
    # Loss of features only matters after validating an actual material actor edge.
    relevant = any(removed in (edge['source'], edge['destination']) for edge in original['edges'])
    if relevant and not reduced['coverage']:
        return 'MULTI_PARTY_DEPENDENCY'
    return 'INCONCLUSIVE'


def excluded_descendants(messages, actor):
    excluded = set()
    for m in messages:
        if m.envelope.actor == actor or m.envelope.parent_message_id in excluded or any(
                x in excluded for x in m.response.contribution.depends_on):
            excluded.add(m.envelope.message_id)
    # Transcript order is reproducible; sorting random UUIDs is not.
    return tuple(m.envelope.message_id for m in messages if m.envelope.message_id in excluded)


def make_draft(run, messages, cfs):
    _, cs = structure(messages, run.scenario)
    return {'actors': [c.actor for c in cs], 'contributions': [c.model_dump(mode='json') for c in cs],
            'sources': list(run.scenario.sources), 'features': list(run.scenario.features),
            'assertions': [c.model_dump(mode='json') for m in messages for c in m.response.claims],
            'assumptions': [ASSUMPTION],
            'limitations': ['No actual misconduct established.', 'Counterfactuals test scripted structure, not causation.'],
            'graph': dependency_graph(messages, run.scenario),
            'cf': [c.model_dump(mode='json') for c in cfs]}


def assemble(run, messages, manifest, recommendation, comparison, cfs):
    complete, cs = structure(messages, run.scenario)
    if not complete:
        return None
    refs = run.scenario.sources
    graph = dependency_graph(messages, run.scenario)
    flows = []
    for edge in graph['edges']:
        flows.append(Flow(source_actor=edge['source'], destination_actor=edge['destination'],
            flow_type='contribution_dependency', trace_ids=(edge['parent'], edge['child']),
            claim=Claim(label='SIMULATION', source_ids=refs,
                text=f"{edge['destination']} explicitly depends on {edge['source']}'s simulated {describe(edge['required_features'])}; this is a scripted relationship.")))
    for c in cs:
        mids = tuple(m.envelope.message_id for m in messages if m.response.contribution == c)
        flows.append(Flow(source_actor='SCHEME', destination_actor=c.actor, flow_type='hypothesized_benefit',
                          trace_ids=mids, claim=c.benefit.model_copy(update={'label': 'ASSUMPTION'})))
    assertions = tuple(claim for m in messages for claim in m.response.claims)
    return Card(pattern_id=uid('pattern'), run_id=run.run_id, scenario=run.scenario,
        source_manifest=dict(manifest), title='Hypothetical ' + run.scenario.scenario_id.replace('_', ' '),
        summary=Claim(label='SIMULATION', source_ids=refs,
            text=f"Hypothetical mechanism involving {', '.join(c.actor for c in cs)}: {describe(run.scenario.features)}. "
                 f"{'Explicit material cooperation' if graph['cooperative'] else 'Single-actor structure' if graph['single'] else 'Cooperation unsubstantiated'} in scripted contributions; no actual misconduct established."),
        actors=tuple(c.actor for c in cs), contributions=cs, flows=tuple(flows),
        assertions=assertions + (Claim(label='ASSUMPTION', text=ASSUMPTION, source_ids=refs),),
        limitations=('Annex A is illustrative; Annex B is exercise-written and unverified.',
                     'Role allocation and benefit endpoints are assumptions, not observed transfers.',
                     'Actor-removal findings concern scripted structure, not real-world causation.'),
        classification=recommendation.classification, comparison_rationale=comparison['rationale'],
        counterfactuals=tuple(cfs), missing_data=recommendation.missing_data,
        trace_ids=tuple(m.envelope.message_id for m in messages), evaluation_ids=(), machine_outcome='BLOCKED')


def evaluate_trace(run, messages, card):
    ids = {m.envelope.message_id for m in messages}
    checks = {
        'nonempty_transcript': bool(messages),
        'bound_identity': all(m.envelope.actor == m.response.contribution.actor for m in messages),
        'ancestry_same_run': all(not m.envelope.parent_message_id or m.envelope.parent_message_id in ids for m in messages),
        'scoped_references': all(set(c.source_ids) <= set(m.envelope.source_ids) for m in messages for c in m.response.claims),
        'participation_matches_contributions': card is None or set(card.actors) == {c.actor for c in card.contributions},
        'source_support': card is None or support(run.scenario.features, run.scenario.sources)['eligible'],
        'benign_control': set(run.scenario.sources) != {'S5'} or card is None,
        'valid_material_graph': not dependency_graph(messages, run.scenario)['errors'],
    }
    return Evaluation(evaluation_id=uid('eval'), fixture_id='candidate_trace_v2', passed=all(checks.values()),
        checks=tuple(k + ':' + str(v) for k, v in checks.items()), trace_ids=tuple(m.envelope.message_id for m in messages))


CANONICAL_VERSION = 'semantic-replay-2'
HUMAN_KINDS = {'human_decision', 'decision_denied', 'step_annotation', 'trusted_revision'}


def canonical(export, *, post_review=False):
    """Complete semantic records, scoped budgets and stable identity relationships.

    Simulation and post-review forms are explicit. Original bytes are never mutated.
    Only clocks, generated IDs, global SQL sequence and raw-output byte hashes (when
    a stable semantic-output hash is present) are normalised. Unknown fields survive.
    """
    source = copy.deepcopy(export)
    names = {}

    def register(value, token):
        if value and value not in names:
            names[value] = token

    def index(e, prefix):
        register(e['run']['id'], prefix)
        for i, r in enumerate(e['records']):
            register(r['id'], f'{prefix}/{r["kind"]}/{i}')
            data = r['data']
            for key in ('invocation_id', 'event_id', 'message_id', 'pattern_id', 'evaluation_id', 'gate_id', 'decision_id', 'annotation_id'):
                register(data.get(key), f'{prefix}/{key}/{i}')
            env = data.get('context', {}).get('envelope', data.get('envelope', {}))
            register(env.get('message_id'), f'{prefix}/message/{env.get("turn")}')
        for child in sorted(e['children'], key=lambda c: json.loads(c['run']['metadata'])['removed_actor']):
            index(child, prefix + '/CF-' + json.loads(child['run']['metadata'])['removed_actor'])
    index(source, 'ROOT')
    # Suite scope is shared by all calls in this TEST, but its random ID is metadata.
    for r in source['records']:
        for scope in r['data'].get('scopes', []):
            if scope.startswith('suite-'):
                register(scope, 'TEST_SUITE')

    def normal(value):
        if isinstance(value, str):
            return names.get(value, value)
        if isinstance(value, list):
            return [normal(x) for x in value]
        if isinstance(value, dict):
            result = {names.get(k, k): normal(v) for k, v in value.items()
                      if k not in ('timestamp', 'elapsed_seconds', 'seq')}
            if isinstance(result.get('calls'), list):
                result['calls'] = sorted(result['calls'], key=lambda b: b['scope'])
            return result
        return value

    def one(e):
        records = []
        simulation_status = e['run']['status']
        for r in e['records']:
            if r['kind'] == 'state_transition':
                simulation_status = r['data']['status']
            if not post_review and r['kind'] in HUMAN_KINDS:
                continue
            data = r['data']
            if r['kind'] == 'invocation':
                if data.get('semantic_output_digest'):
                    data.pop('output_digest', None)
                if data.get('raw_output'):
                    try:
                        data['raw_output'] = normal(json.loads(data['raw_output']))
                    except ValueError:
                        pass
            records.append(normal({'id': r['id'], 'kind': r['kind'], 'data': data}))
        run = dict(e['run'], metadata=json.loads(e['run']['metadata']))
        if not post_review:
            run['status'] = simulation_status
            run.pop('version', None)
        scopes = {e['run']['id']}
        for r in e['records']:
            if r['kind'] == 'usage':
                scopes.update(r['data']['scopes'])
        # Usage of an unrelated run or later TEST suite fixture is not this result.
        local_usage = sum(r['kind'] == 'invocation_started' for r in e['records'])
        budgets = sorted((normal(dict(b, used=local_usage if b['scope'] != e['run']['id'] else b['used']))
                          for b in e['budgets'] if b['scope'] in scopes), key=lambda b: b['scope'])
        return {'run': normal(run), 'records': records, 'budgets': budgets,
                'decisions': normal(e['decisions']) if post_review else [],
                'annotations': normal(e['annotations']) if post_review else [],
                'children': [one(c) for c in sorted(e['children'], key=lambda c: json.loads(c['run']['metadata'])['removed_actor'])]}
    return {'canonical_version': CANONICAL_VERSION,
            'scope': 'post-review' if post_review else 'simulation', 'result': one(source)}
