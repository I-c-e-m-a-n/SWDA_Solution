"""Trusted finite scheduler. Models receive data, never application services."""
import json
import hashlib
import time
from pydantic import ValidationError
from .schemas import (Scenario, Profile, Limits, Run, Envelope, Response, Invocation,
                      Recommendation, Counterfactual, Gate, Context, Message)
from .sources import ROOT, Catalogue
from .store import Store, uid
from .policy import Gateway, Denied
from .models import adapters
from .grounding import support, REGISTRY_VERSION
from .analysis import (compare, structure, assemble, excluded_descendants, evaluate_trace,
                       make_draft, dependency_graph, cf_outcome)


def scenarios():
    return {s.scenario_id:s for s in (Scenario.model_validate_json(json.dumps(x))
            for x in json.loads((ROOT/'config/scenarios.json').read_text()))}


def profiles():
    conf = json.loads((ROOT/'config/profiles.json').read_text())
    if conf['version'] != 'acl-1':
        raise ValueError('POLICY_VERSION')
    return {p.actor:p for p in (Profile.model_validate_json(json.dumps(x)) for x in conf['profiles'])}


class Orchestrator:
    def __init__(self, store: Store, limits=None, source_path=None, model_factory=adapters, clock=time.monotonic):
        self.store, self.source_path, self.clock = store, source_path, clock
        self.limits = Limits.model_validate_json(limits.model_dump_json() if limits else (ROOT/'config/limits.json').read_text())
        self.model_factory = model_factory

    def snapshot(self, scenario, cat, ps):
        return {'source_manifest':dict(cat.manifest),
                'policy':{k:v.model_dump(mode='json') for k,v in ps.items()},
                'limits':self.limits.model_dump(mode='json'), 'scenario':scenario.model_dump(mode='json'),
                'code_version':'1.1.0',
                'code_revision':'sha256:'+hashlib.sha256(b''.join(
                    p.name.encode()+p.read_bytes() for p in sorted((ROOT/'src/swda_part2c').glob('*.py')))).hexdigest(),
                'schema_version':'2', 'adapter_version':'scripts-2', 'grounding_version':REGISTRY_VERSION}

    def execute(self, scenario: Scenario, kind='CANDIDATE', parent=None, removed=None,
                suite=None, parent_messages=()):
        # A model has no reference to execute. All derived calls come from this finite scheduler.
        scenario = Scenario.model_validate_json(scenario.model_dump_json())
        run = Run(run_id=uid('run'), run_type=kind, parent_run_id=parent, removed_actor=removed,
                  scenario=scenario, depth=1 if kind=='CF' else 0)
        if kind == 'CF':
            # Admission is authoritative and atomic; no executable child exists on rejection.
            cat, ps = Catalogue(self.source_path), profiles()
            snapshot = self.snapshot(scenario, cat, ps)
            self.store.create_run(run, snapshot)
            # Parent data is resolved from persistence, never a caller's taint assertion.
            parent_messages = tuple(Message.model_validate_json(json.dumps(r['data']))
                                    for r in self.store.records(parent, 'message'))
        else:
            self.store.create_run(run)
        started = self.clock()
        messages, cfs = [], []
        card = None
        try:
            if self.source_path and self.source_path.name == 'annex-injection-v1.json' and kind != 'TEST':
                raise ValueError('ADVERSARIAL_FIXTURE_TEST_ONLY')
            cat = Catalogue(self.source_path)
            if scenario.source_version != cat.version or scenario.fixture_version != 'scripts-2':
                raise ValueError('PINNED_VERSION_UNAVAILABLE')
            ps = profiles()
            if scenario.policy_version != 'acl-1':
                raise ValueError('POLICY_VERSION')
            cat.read(scenario.sources)
            if kind=='CF':
                pinned=self.store.records(parent,'snapshots')[0]['data']
                if pinned['source_manifest']!=dict(cat.manifest) or pinned['policy']!={k:v.model_dump(mode='json') for k,v in ps.items()}:
                    raise ValueError('CF_RELEASE_PIN_MISMATCH')
            gateway = Gateway(cat, ps, self.store)
            models = self.model_factory()  # Fresh adapters for every CANDIDATE/CF/TEST.
            if set(models) != {'TA','PA','EA','REV'}:
                raise ValueError('EXACTLY_FOUR_ADAPTERS_REQUIRED')
            if kind != 'CF':
                self.store.record(run.run_id, 'snapshots', self.snapshot(scenario, cat, ps))
            grounding = support(scenario.features, scenario.sources)
            self.store.record(run.run_id, 'grounding', grounding)
            if scenario.features and not grounding['eligible']:
                self.store.record(run.run_id, 'no_pattern', {'reason':'Unsupported risk mechanism; all configured features retained.',
                                                          'grounding':grounding})
                self.store.finish(run.run_id, 'NO_PATTERN')
                return self.store.export(run.run_id)
            local_scope = run.run_id
            aggregate = parent or run.run_id
            local_cap = self.limits.test_calls if kind=='TEST' else self.limits.lineage_calls
            self.store.budget(local_scope, local_cap)
            if kind=='CF':
                self.store.budget(aggregate, self.limits.lineage_calls)
            if suite:
                if kind != 'TEST':
                    raise ValueError('SUITE_REQUIRES_TEST')
                self.store.budget(suite, self.limits.suite_calls)
            scopes = list(dict.fromkeys([local_scope, aggregate]+([suite] if suite else [])))

            def check(round_no=1, turn=1):
                if self.clock()-started >= self.limits.seconds:
                    raise ValueError('TIMEOUT')
                if round_no > self.limits.rounds:
                    raise ValueError('ROUND_BUDGET_EXHAUSTED')
                if turn > self.limits.turns:
                    raise ValueError('TURN_BUDGET_EXHAUSTED')

            def invoke(ctx, schema):
                for attempt in range(self.limits.retries+1):
                    check(ctx.envelope.round, ctx.envelope.turn)
                    env = ctx.envelope.model_copy(update={'attempt':attempt})
                    scoped = ctx.model_copy(update={'envelope':env})
                    invocation_id = uid('inv')
                    invocation_start = {'invocation_id':invocation_id, 'context':scoped.model_dump(mode='json'),
                                        'schema_version':'2', 'script_version':scenario.fixture_version}
                    self.store.consume(scopes, run_id=run.run_id, invocation=invocation_start,
                        usage={'scopes':scopes, 'attempt':attempt, 'message_id':env.message_id,
                               'invocation_id':invocation_id, 'elapsed_seconds':self.clock()-started})
                    raw, outcome, error = '', 'ADAPTER_EXCEPTION', ''
                    try:
                        model_context = Context.model_validate_json(scoped.model_dump_json())
                        raw = models[env.actor].generate(model_context)
                        outcome = 'OVERSIZED_OUTPUT'
                        if not isinstance(raw, str) or len(raw.encode()) > 16000:
                            raise Denied('OUTPUT_SIZE_LIMIT')
                        outcome = 'TIMEOUT'
                        check(env.round, env.turn)
                        try:
                            parsed = json.loads(raw)
                        except (ValueError, TypeError):
                            parsed = None
                        outcome = 'OPERATION_DENIED'
                        if isinstance(parsed, dict) and 'operation' in parsed and (
                            schema is not Response or parsed['operation'] != env.purpose):
                            gateway.verdict(env, 'receipt', False, 'OPERATION_DENIED')
                        outcome = 'SCHEMA_ERROR'
                        response = schema.model_validate_json(raw)
                        outcome = 'POLICY_VIOLATION'
                        accepted = gateway.receipt(scoped, response) if schema is Response else response
                        outcome = 'SCHEMA_VALID'  # Successfully validated AND accepted.
                        return scoped, accepted
                    except ValidationError:
                        error = 'SCHEMA_VALIDATION_FAILED'
                        self.store.event(run.run_id, 'schema_retry', {'attempt':attempt, 'scope':env.model_dump(mode='json')}, env.actor)
                        if attempt == self.limits.retries:
                            raise ValueError('SCHEMA_RETRIES_EXHAUSTED')
                    except Exception as exc:
                        error = str(exc) if isinstance(exc, (Denied, ValueError)) and str(exc).isupper() else type(exc).__name__
                        raise
                    finally:
                        payload = raw if isinstance(raw, str) else type(raw).__name__
                        # Preserve bytes' hash; stable semantic hash removes only trusted generated IDs.
                        normal = payload
                        replacements = {env.run_id:'RUN', env.message_id:'CURRENT_MESSAGE'}
                        for m in (*scoped.incoming, *scoped.prior):
                            replacements[m.envelope.message_id] = f'MESSAGE:{m.envelope.actor}:{m.envelope.turn}'
                        for key, value in replacements.items():
                            normal = normal.replace(key, value)
                        self.store.record(run.run_id, 'invocation', Invocation(invocation_id=invocation_id,
                            context=scoped, raw_output=payload if outcome == 'SCHEMA_VALID' else '',
                            outcome=outcome, error_code=error,
                            output_digest=hashlib.sha256(payload.encode()).hexdigest(),
                            semantic_output_digest=hashlib.sha256(normal.encode()).hexdigest(),
                            output_bytes=len(payload.encode())), invocation_id)
                raise AssertionError('unreachable')

            active = tuple(a for a in scenario.roles if a != removed)
            self.store.record(run.run_id, 'context_reset', {'fresh_history':True,
                'removed_actor':removed, 'copied_parent_messages':[],
                'excluded_parent_messages':list(excluded_descendants(parent_messages, removed)) if removed else []})
            turn = 0
            for round_no in range(1, scenario.rounds+1):
                for i, actor in enumerate(active):
                    turn += 1
                    check(round_no, turn)
                    incoming = tuple(m for m in messages if m.envelope.recipient == actor)
                    prior = tuple(m for m in messages if m.envelope.actor == actor)
                    recipient = active[i+1] if i+1 < len(active) else 'ORCH'
                    env = Envelope(run_id=run.run_id, run_type=kind, message_id=uid('msg'),
                        parent_message_id=incoming[-1].envelope.message_id if incoming else None,
                        actor=actor, recipient=recipient, purpose='reply' if incoming else 'propose',
                        source_ids=scenario.sources, policy_version=scenario.policy_version,
                        source_version=scenario.source_version, round=round_no, turn=turn, attempt=0)
                    ctx = gateway.dispatch(env, scenario, incoming, prior)
                    ctx, response = invoke(ctx, Response)
                    messages.append(response)
            check()
            supported, cs = structure(messages, scenario)
            if kind == 'CF':
                self.store.record(run.run_id, 'cf_structure', {'supported':supported,
                    'actors':[c.actor for c in cs], 'features':sorted({f for c in cs for f in c.features}),
                    'graph':dependency_graph(messages, scenario)})
                self.store.finish(run.run_id, 'COMPLETE')
                return self.store.export(run.run_id)
            if not supported:
                evaluation = evaluate_trace(run, messages, None)
                self.store.record(run.run_id, 'evaluation', evaluation, evaluation.evaluation_id)
                self.store.record(run.run_id, 'no_pattern', {'reason':'Benign control' if scenario.mode=='benign'
                    else 'Insufficient attributable contributions; no supported pattern.'})
                self.store.finish(run.run_id, 'NO_PATTERN')
                return self.store.export(run.run_id)
            if kind == 'CANDIDATE':
                for c in cs:
                    check()
                    if len(cfs) >= self.limits.cf:
                        raise ValueError('CF_BUDGET_EXHAUSTED')
                    try:
                        cf = self.execute(scenario, 'CF', parent=run.run_id, removed=c.actor)
                    except ValueError as exc:
                        self.store.record(run.run_id, 'cf_admission_denied', {'removed_actor':c.actor, 'reason':str(exc)})
                        result = Counterfactual(run_id='', parent_run_id=run.run_id, removed_actor=c.actor,
                            outcome='INCONCLUSIVE', surviving_actors=(), excluded_parent_messages=excluded_descendants(messages, c.actor),
                            rationale='No reduced execution admitted: '+str(exc))
                    else:
                        cf_messages = [Message.model_validate_json(json.dumps(r['data']))
                                       for r in cf['records'] if r['kind']=='message']
                        _, survivors = structure(cf_messages, scenario)
                        outcome = cf_outcome(messages, cf_messages, scenario, cf['run']['status']=='COMPLETE', c.actor)
                        result = Counterfactual(run_id=cf['run']['id'], parent_run_id=run.run_id,
                            removed_actor=c.actor, outcome=outcome, surviving_actors=tuple(x.actor for x in survivors),
                            excluded_parent_messages=excluded_descendants(messages, c.actor),
                            rationale='Fresh reduced execution compared with validated material dependency edges and feature coverage. '
                                      'A surviving coalition is not single-actor feasibility; loss without parent cooperation is inconclusive. '
                                      'No real-world causal proof is claimed.')
                    cfs.append(result)
                    self.store.record(run.run_id, 'counterfactual', result)
            check()
            # Review lookup is itself mediated. Reviewer has no catalogue or gateway object.
            mo_ids = tuple(f'MO-{i:02}' for i in range(1,9))
            ids = tuple(dict.fromkeys(mo_ids+scenario.sources))
            # Reviewer consumes an actor turn, so the 12-turn cap includes review.
            turn += 1
            check(1, turn)
            env = Envelope(run_id=run.run_id, run_type=kind, message_id=uid('review'),
                parent_message_id=None, actor='REV', recipient='GATE', purpose='review', source_ids=ids,
                policy_version=scenario.policy_version, source_version=scenario.source_version,
                round=1, turn=turn, attempt=0)
            draft = make_draft(run, messages, cfs)
            ctx = gateway.dispatch(env, scenario, draft=draft)
            request = models['REV'].reference_request(ctx)
            # Revalidate custom-adapter requests, rather than trusting Python return annotations.
            from .schemas import Lookup
            request = Lookup.model_validate_json(request.model_dump_json())
            references = gateway.lookup(env, request)
            comparison = compare({f for c in cs for f in c.features}, references)
            ctx = ctx.model_copy(update={'references':references, 'comparison':comparison})
            _, recommendation = invoke(ctx, Recommendation)
            self.store.record(run.run_id, 'recommendation', recommendation)
            card = assemble(run, messages, cat.manifest, recommendation, comparison, cfs)
            if not card:
                raise ValueError('ASSEMBLY_FAILED')
            evaluation = evaluate_trace(run, messages, card)
            self.store.record(run.run_id, 'evaluation', evaluation, evaluation.evaluation_id)
            from .safety import assess
            gates = assess(run, card, messages, cat, self.store, evaluation, recommendation, comparison)
            # TEST can pass evaluation but always fails human eligibility by design.
            for name, passed in gates.items():
                gate = Gate(gate_id=uid('gate'),name=name,passed=bool(passed),
                            evidence=(evaluation.evaluation_id,),reason='Trusted deterministic '+name)
                self.store.record(run.run_id,'gate',gate,gate.gate_id)
            passed = all(v for k,v in gates.items() if k!='human_review_eligibility')
            card = card.model_copy(update={'machine_outcome':'PASS' if passed else 'BLOCKED',
                'evaluation_ids':(evaluation.evaluation_id,),
                'human_status':'REVIEW_PENDING' if kind=='CANDIDATE' and all(gates.values()) else 'NOT_ELIGIBLE'})
            if len(self.store.records(run.run_id,'card')) >= self.limits.cards:
                raise ValueError('CARD_BUDGET_EXHAUSTED')
            self.store.record(run.run_id,'card',card,card.pattern_id)
            check()
            status = 'REVIEW_PENDING' if kind=='CANDIDATE' and all(gates.values()) else 'COMPLETE' if kind=='TEST' and passed else 'BLOCKED'
            self.store.finish(run.run_id,status)
        except (ValueError, KeyError, OSError) as exc:
            self.store.event(run.run_id,'execution_blocked',{'code':str(exc), 'calls':self.store.usage_for(run.run_id)})
            gate = Gate(gate_id=uid('gate'),name='execution_integrity',passed=False,
                        evidence=(),reason=str(exc))
            self.store.record(run.run_id,'gate',gate,gate.gate_id)
            self.store.finish(run.run_id,'BLOCKED')
        return self.store.export(run.run_id)
