"""The single OUT/IN/POL gateway. Denied payloads are never delivered."""
from .schemas import Context, Envelope, Response, PolicyDecision, Lookup
from .grounding import FEATURES, support, contribution_text, benefit_text

class Denied(ValueError):
    pass

# Closed response grammar is stronger than keyword checks for these supplied mocks.
# A future adapter must be assessed separately; this is not a general language safety classifier.
SAFE_CLAIMS = {
    'TA': 'Hypothetical trainee contribution; participation and benefit remain unverified.',
    'PA': 'Hypothetical provider contribution; delivery and benefit remain unverified.',
    'EA': 'Hypothetical employer contribution; employment and benefit remain unverified.',
}
BENEFITS = {
    'TA': 'Hypothetical training-related benefit; no actual benefit is established.',
    'PA': 'Hypothetical enrolment-related benefit; no actual benefit is established.',
    'EA': 'Hypothetical employment-related benefit; no actual benefit is established.',
}
ASSUMPTION = 'Role incentives and structural dependencies are scripted modelling assumptions.'

class Gateway:
    def __init__(self, catalogue, profiles, store):
        self.catalogue, self.profiles, self.store = catalogue, profiles, store
        self.delivered = {}

    def verdict(self, env, stage, allowed, code):
        decision = PolicyDecision(allowed=allowed, stage=stage, code=code, message_id=env.message_id)
        self.store.record(env.run_id, 'policy', decision)
        if not allowed:
            raise Denied(code)

    def dispatch(self, env: Envelope, scenario, incoming=(), prior=(), draft=None, comparison=None):
        p = self.profiles[env.actor]
        ok = (env.policy_version == scenario.policy_version == 'acl-1'
              and env.source_version == scenario.source_version == self.catalogue.version
              and set(env.source_ids) <= set(p.sources)
              and env.recipient in p.recipients and env.purpose in p.capabilities
              and (env.actor == 'REV' or set(env.source_ids) <= set(scenario.sources)))
        for m in incoming:
            ok &= (m.envelope.recipient == env.actor and m.envelope.run_id == env.run_id
                   and self.delivered.get(m.envelope.message_id) == m)
        for m in prior:
            ok &= (m.envelope.actor == env.actor and m.envelope.run_id == env.run_id
                   and self.delivered.get(m.envelope.message_id) == m)
        if env.parent_message_id:
            ok &= any(m.envelope.message_id == env.parent_message_id for m in incoming)
        self.verdict(env, 'dispatch', bool(ok), 'DISPATCH_ALLOWED' if ok else 'DISPATCH_DENIED')
        return Context(envelope=env, profile=p, scenario=scenario,
                       references=() if env.actor == 'REV' else self.catalogue.read(env.source_ids), incoming=tuple(incoming),
                       prior=tuple(prior), draft=draft, comparison=comparison)

    def receipt(self, ctx: Context, response: Response):
        env, p = ctx.envelope, ctx.profile
        claims = (*response.claims, response.contribution.claim, response.contribution.benefit)
        c = response.contribution
        refs = {r.source_id: r for r in ctx.references}
        ancestry = {m.envelope.message_id for m in ctx.incoming if m.response.contribution.material}
        allowed = (response.recipient == env.recipient and response.operation == env.purpose
                   and c.actor == env.actor and set(c.depends_on) <= ancestry
                   and set(c.features) <= FEATURES and set(c.features) <= set(ctx.scenario.features)
                   and all(set(x.source_ids) <= set(env.source_ids) for x in claims))
        if response.recipient in self.profiles:
            allowed &= set(env.source_ids) <= set(self.profiles[response.recipient].sources)
        self.verdict(env, 'receipt', bool(allowed), 'RECEIPT_ALLOWED' if allowed else 'RECEIPT_DENIED')
        parents = {m.envelope.message_id: m for m in ctx.incoming}
        dependency_ok = (set(c.dependency_features) == set(c.depends_on)
                         and len(c.depends_on) == len(set(c.depends_on)))
        for mid in c.depends_on:
            previous = parents[mid]
            pc = previous.response.contribution
            required = c.dependency_features.get(mid, ())
            dependency_ok &= (previous.envelope.turn < env.turn and previous.envelope.actor != env.actor
                              and previous.envelope.run_id == env.run_id and pc.material and c.material
                              and bool(pc.features) and bool(c.features) and bool(required)
                              and set(required) <= set(pc.features)
                              and bool(set(c.features) - set(pc.features)))
        self.verdict(env, 'dependency', bool(dependency_ok),
                     'DEPENDENCY_ALLOWED' if dependency_ok else 'INVALID_MATERIAL_DEPENDENCY')
        grounded = not c.material or (bool(c.features)
            and support(c.features, c.claim.source_ids)['eligible']
            and support(c.features, c.benefit.source_ids)['eligible'])
        self.verdict(env, 'grounding', grounded, 'CONCEPT_SUPPORTED' if grounded else 'UNSUPPORTED_FEATURE_SOURCE')
        # Exact attributed quotations and approved risk-level prose only.
        for claim in claims:
            safe = (claim.label == 'SOURCE' and len(claim.source_ids) == 1
                    and claim.text == refs[claim.source_ids[0]].text)
            safe |= claim.label == 'SIMULATION' and claim.text in (
                contribution_text(c.actor, c.features), benefit_text(c.actor, c.features))
            safe |= claim.label == 'ASSUMPTION' and claim.text == ASSUMPTION
            if not safe:
                self.verdict(env, 'safety', False, 'UNSAFE_OR_UNSUPPORTED_OUTPUT')
        self.verdict(env, 'safety', True, 'SAFE_CLOSED_GRAMMAR')
        from .schemas import Message
        message = Message(envelope=env, response=response)
        if env.message_id in self.delivered:
            raise Denied('DUPLICATE_MESSAGE')
        self.delivered[env.message_id] = message
        self.store.record(env.run_id, 'message', message, env.message_id)
        return message

    def lookup(self, env, request: Lookup):
        p = self.profiles['REV']
        allowed = env.actor == 'REV' and set(request.source_ids) <= set(p.sources)
        allowed &= set(request.source_ids) <= set(env.source_ids)
        self.store.record(env.run_id, 'reviewer_lookup',
                          {'requested': request.model_dump(mode='json'), 'allowed': bool(allowed),
                           'returned_ids': list(request.source_ids) if allowed else []})
        self.verdict(env, 'reviewer_lookup', bool(allowed), 'LOOKUP_ALLOWED' if allowed else 'LOOKUP_DENIED')
        # Only validated immutable source records cross the return path.
        return tuple(type(r).model_validate_json(r.model_dump_json()) for r in self.catalogue.read(request.source_ids))
