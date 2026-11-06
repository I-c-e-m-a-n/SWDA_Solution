"""Four separately configured mock adapters behind one future-adapter interface."""
import json
from typing import Protocol
from .schemas import Context, Lookup
from .policy import SAFE_CLAIMS, BENEFITS, ASSUMPTION
from .grounding import contribution_text, benefit_text

class Model(Protocol):
    def generate(self, context: Context) -> str: ...
    def reference_request(self, context: Context) -> Lookup: ...

class ScriptedActor:
    def __init__(self, actor, script_version, style):
        self.actor, self.script_version, self.style = actor, script_version, style

    def generate(self, context):
        e, s = context.envelope, context.scenario
        assert e.actor == self.actor
        if s.fault == 'malformed' or (s.fault == 'repair' and e.attempt == 0):
            return '{invalid'
        position = s.roles.index(self.actor)
        predecessor = s.roles[position-1] if position else None
        parents = [m for m in context.incoming if m.envelope.actor == predecessor
                   and m.response.contribution.material]
        material = (s.mode == 'single' or (s.mode == 'dependency' and (position == 0 or bool(parents))))
        # Each role contributes only its feature slice. A downstream role needs an authorised
        # predecessor. Fresh CF histories must rebuild this chain; names alone cannot do so.
        features = s.features[position::len(s.roles)] if material else ()
        refs = tuple(r.source_id for r in context.references)
        source = context.references[(s.seed + e.round + len(context.prior)) % len(context.references)]
        claim = lambda label, text, ids=refs: dict(label=label, text=text, source_ids=list(ids))
        out = dict(operation=e.purpose, recipient=e.recipient,
                   claims=[claim('SOURCE', source.text, (source.source_id,)), claim('ASSUMPTION', ASSUMPTION)],
                   contribution=dict(actor=self.actor, claim=claim('SIMULATION', contribution_text(self.actor, features)),
                                     benefit=claim('SIMULATION', benefit_text(self.actor, features)), features=list(features),
                                     depends_on=[m.envelope.message_id for m in parents[-1:]],
                                     dependency_features={m.envelope.message_id:list(m.response.contribution.features)
                                                          for m in parents[-1:]},
                                     material=material and bool(features)))
        if s.fault == 'recipient':
            out['recipient'] = 'APPROVAL'
        if s.fault == 'sender':
            out['contribution']['actor'] = 'EA' if self.actor != 'EA' else 'TA'
        if s.fault == 'source':
            out['claims'][0]['source_ids'] = ['S99']
        if s.fault == 'unsafe':
            out['contribution']['claim']['text'] = 'Operational wrongdoing instructions are requested.'
        if s.fault == 'unsupported':
            out['contribution']['claim']['text'] = 'Actual misconduct has been proven by this simulation.'
        if s.fault == 'operation':
            out['operation'] = 'approve'
        # Injection fixtures are supplied as inert Source.text; never parsed as instructions.
        return json.dumps(out)

    def reference_request(self, context):
        raise ValueError('ACTOR_HAS_NO_LOOKUP_CAPABILITY')

class ScriptedReviewer:
    def reference_request(self, context):
        ids = ('S99',) if context.scenario.fault == 'reviewer_lookup' else context.envelope.source_ids
        return Lookup(purpose='mo_comparison', source_ids=ids)

    def generate(self, context):
        if context.scenario.fault == 'reviewer_invalid':
            return '{}'
        from .review import review
        return review(context).model_dump_json()


def adapters():
    return {'TA': ScriptedActor('TA', 'scripts-2', 'trainee'),
            'PA': ScriptedActor('PA', 'scripts-2', 'provider'),
            'EA': ScriptedActor('EA', 'scripts-2', 'employer'),
            'REV': ScriptedReviewer()}
