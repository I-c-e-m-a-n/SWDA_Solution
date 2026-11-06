"""Reviewed annex concept mapping, not a factual evidence or general NLP classifier.

Only direct illustrative MO support permits a risk concept. Excerpts can add weak
context or benign counter-signals, never establish misconduct. No feature is dropped.
Changing this registry is a trusted code-release change, pinned by the code digest.
"""
REGISTRY_VERSION = 'annex-concepts-1'
SIGNATURES = {
    'MO-01': {'dormant_employer', 'dormant_provider'},
    'MO-02': {'false_records', 'audit_check'},
    'MO-03': {'false_claim', 'nonattendance'},
    'MO-04': {'cash_offer', 'credit_use', 'optional_attendance'},
    'MO-05': {'attendance_record', 'undelivered_training'},
    'MO-06': {'employment_link', 'course_only', 'employment_end'},
    'MO-07': {'claim_exceeds_delivery'},
    'MO-08': {'sponsor_fee', 'provider_return'},
}
CONTEXT = {
    'S1': {'bundling_value_hypothesis'}, 'S2': {'price_value_hypothesis'},
    'S3': {'cash_offer', 'credit_use'}, 'S4': {'assessment_quality_concern'},
}
FEATURES = frozenset().union(*SIGNATURES.values(), *CONTEXT.values())
DESCRIPTIONS = {
    'dormant_employer': 'dormant employer participation', 'dormant_provider': 'dormant provider participation',
    'false_records': 'unreliable supporting records', 'audit_check': 'claim-check evidence',
    'false_claim': 'a potentially unsupported grant claim', 'nonattendance': 'nonattendance',
    'cash_offer': 'a cash inducement', 'credit_use': 'training-credit use',
    'optional_attendance': 'attendance represented as optional',
    'attendance_record': 'an attendance representation', 'undelivered_training': 'undelivered training',
    'employment_link': 'an employment link', 'course_only': 'course-only employment',
    'employment_end': 'employment ending after training', 'claim_exceeds_delivery': 'claims exceeding delivery',
    'sponsor_fee': 'sponsor fee support', 'provider_return': 'value returning through a provider',
    'bundling_value_hypothesis': 'course bundling concerns', 'price_value_hypothesis': 'price/value concerns',
    'assessment_quality_concern': 'assessment-quality concerns',
}
DATA = {
    'enrolment_records': 'Independently verified enrolment records',
    'attendance_records': 'Independently verified attendance records',
    'training_delivery_records': 'Independently verified training-delivery records',
    'employment_records': 'Independently verified employment records',
    'grant_claim_records': 'Independently verified grant-claim records',
    'value_flow_records': 'Independently verified financial or value-flow records',
}
FEATURE_DATA = {
    **{f: ('grant_claim_records', 'employment_records') for f in SIGNATURES['MO-01']},
    **{f: ('grant_claim_records', 'training_delivery_records') for f in SIGNATURES['MO-02']},
    **{f: ('grant_claim_records', 'attendance_records') for f in SIGNATURES['MO-03']},
    **{f: ('enrolment_records', 'attendance_records', 'value_flow_records') for f in SIGNATURES['MO-04']},
    **{f: ('attendance_records', 'training_delivery_records') for f in SIGNATURES['MO-05']},
    **{f: ('employment_records', 'enrolment_records') for f in SIGNATURES['MO-06']},
    'claim_exceeds_delivery': ('grant_claim_records', 'training_delivery_records'),
    **{f: ('value_flow_records', 'enrolment_records') for f in SIGNATURES['MO-08']},
}


def support(features, source_ids):
    """Categorise every requested concept independently of scenario mode."""
    ids = set(source_ids)
    rows = {}
    for feature in sorted(features):
        direct = sorted(k for k, fs in SIGNATURES.items() if k in ids and feature in fs)
        weak = sorted(k for k, fs in CONTEXT.items() if k in ids and feature in fs)
        rows[feature] = {'direct': direct, 'context': weak,
                         'level': 'DIRECT_CONCEPT' if direct else 'WEAK_CONTEXT' if weak else 'UNSUPPORTED'}
    return {'version': REGISTRY_VERSION, 'features': rows,
            'benign': sorted(ids & {'S5'}),
            'unsupported': sorted(f for f, row in rows.items() if not row['direct']),
            'eligible': bool(rows) and all(row['direct'] for row in rows.values()),
            'evidence': 'Illustrative risk concepts only; no evidence of actual wrongdoing.'}


def relevant_data(features):
    return tuple(DATA[k] for k in sorted({k for f in features for k in FEATURE_DATA.get(f, ())}))


def valid_data(values, features):
    return bool(values) and len(values) == len(set(values)) and set(values) <= set(relevant_data(features))


def describe(features):
    return ', '.join(DESCRIPTIONS[f] for f in features) or 'no supported risk contribution'


def contribution_text(actor, features):
    return f'Hypothetical {actor} contribution: {describe(features)}. Role allocation is a modelling assumption, not observed conduct.'


def benefit_text(actor, features):
    role_benefit = {'TA': 'training-related value or reduced attendance effort',
                    'PA': 'enrolment or funding-related value', 'EA': 'employment or sponsorship-related value'}
    return f'Hypothesized {actor} benefit: {role_benefit[actor]} in a scenario concerning {describe(features)}; no realised benefit is established.'
