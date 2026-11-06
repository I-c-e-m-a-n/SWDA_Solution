"""Human-only approval and step oversight. Success receipts follow SQLite commit."""
from datetime import datetime, timezone
import getpass
import json
import hashlib
import sqlite3
from pathlib import Path
from .schemas import HumanDecision, StepAnnotation
from .store import uid, dump
from .sources import ROOT

ACTIONS = {'APPROVE_FOR_INVESTIGATION':'APPROVED_FOR_INVESTIGATION',
           'REJECT':'REJECTED','REQUEST_REVISION':'REVISION_REQUESTED'}
REQUIRED_GATES = {'source_integrity','schema_validity','source_reference_allowlisting','assertion_provenance',
                  'policy_compliance','bounded_execution','output_safety','counterfactual_evidence',
                  'reviewer_validity','required_evaluation','human_review_eligibility'}

class ApprovalService:
    def __init__(self, store, reviewer_path=None, current_user=getpass.getuser):
        self.store = store
        self.reviewer_path = Path(reviewer_path or ROOT/'config/reviewers.json')
        self.current_user = current_user

    def authorise(self, reviewer, origin):
        conf = json.loads(self.reviewer_path.read_text())
        if origin!='human' or reviewer!=self.current_user() or reviewer not in conf['reviewers']:
            raise PermissionError('LOCAL_HUMAN_ROLE_REQUIRED')

    def decide(self, request: HumanDecision):
        try:
            return self._decide(request)
        except Exception as exc:
            # The decision context has already rolled back, including COMMIT failures.
            # Denial evidence uses a separate transaction and can never issue a receipt.
            code = str(exc) if isinstance(exc, (ValueError, PermissionError)) and str(exc).isupper() else type(exc).__name__
            try:
                self.store.record(request.run_id, 'decision_denied', {
                    'outcome':'DENIED', 'success_receipt':False, 'reason':code,
                    'reviewer_hash':hashlib.sha256(request.reviewer.encode()).hexdigest(),
                    'origin':request.origin if request.origin in ('human','model') else 'invalid',
                    'action':request.action if request.action in ACTIONS else 'invalid',
                    'expected_version':request.expected_version})
            except Exception as audit_error:
                raise RuntimeError('DECISION_DENIED_AUDIT_PERSISTENCE_FAILED:'+type(audit_error).__name__) from exc
            raise

    def _decide(self, request: HumanDecision):
        # Revalidation closes model_copy/construct bypasses in trusted caller tests.
        request = HumanDecision.model_validate_json(request.model_dump_json())
        self.authorise(request.reviewer, request.origin)
        if not request.explicit_action or len(request.rationale.strip().split())<3:
            raise ValueError('EXPLICIT_ACTION_SUBSTANTIVE_RATIONALE_REQUIRED')
        receipt = dict(decision_id=uid('decision'), **request.model_dump(mode='json'),
                       timestamp=datetime.now(timezone.utc).isoformat(),
                       status=ACTIONS[request.action], committed_version=request.expected_version+1,
                       scope='Further investigation only; never a fraud finding.')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            run = db.execute('SELECT * FROM runs WHERE id=?',(request.run_id,)).fetchone()
            if not run or run['kind']!='CANDIDATE' or run['status']!='REVIEW_PENDING' or run['version']!=request.expected_version:
                raise ValueError('STALE_OR_INELIGIBLE_STATE')
            gates = [json.loads(r[0]) for r in db.execute("SELECT data FROM records WHERE run_id=? AND kind='gate'",(request.run_id,))]
            if {g['name'] for g in gates}!=REQUIRED_GATES or not all(g['passed'] for g in gates):
                raise ValueError('PERSISTED_GATES_REQUIRED')
            if db.execute("SELECT 1 FROM annotations WHERE (run_id=? OR run_id IN (SELECT id FROM runs WHERE parent=?)) AND action IN ('REJECTED','DISPUTED')",
                          (request.run_id,request.run_id)).fetchone():
                raise ValueError('MATERIAL_STEP_CHALLENGED')
            cur = db.execute("UPDATE runs SET status=?,version=version+1 WHERE id=? AND status='REVIEW_PENDING' AND version=?",
                (receipt['status'],request.run_id,request.expected_version))
            if cur.rowcount!=1:
                raise ValueError('CAS_CONFLICT')
            db.execute('INSERT INTO decisions VALUES(?,?,?)',(receipt['decision_id'],request.run_id,dump(receipt)))
            self.store.record(request.run_id,'human_decision',receipt,receipt['decision_id'],db=db)
        return receipt  # The connection context committed successfully before this line.

    def annotate(self, request: StepAnnotation):
        request = StepAnnotation.model_validate_json(request.model_dump_json())
        self.authorise(request.reviewer,request.origin)
        if not request.explicit_action or len(request.rationale.strip().split())<3:
            raise ValueError('ANNOTATION_RATIONALE_REQUIRED')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            run = db.execute('SELECT * FROM runs WHERE id=?',(request.run_id,)).fetchone()
            if not run or run['kind'] not in ('CANDIDATE','CF') or run['status']=='RUNNING':
                raise ValueError('ANNOTATION_RUN_INELIGIBLE')
            root = run if run['kind']=='CANDIDATE' else db.execute('SELECT * FROM runs WHERE id=?',(run['parent'],)).fetchone()
            if not root or root['kind']!='CANDIDATE' or root['status']=='RUNNING':
                raise ValueError('ANNOTATION_LINEAGE_INVALID')
            if run['kind']=='CF' and (json.loads(run['metadata'])['depth']!=1 or run['parent']!=root['id']):
                raise ValueError('ANNOTATION_LINEAGE_INVALID')
            if request.candidate_run_id is not None and request.candidate_run_id!=root['id']:
                raise ValueError('ANNOTATION_CROSS_CANDIDATE')
            if request.expected_version != root['version']:
                raise ValueError('ANNOTATION_STALE_VERSION')
            row = db.execute('SELECT kind FROM records WHERE id=? AND run_id=?',(request.step_id,request.run_id)).fetchone()
            if not row or row['kind'] not in ('message','invocation','invocation_started','counterfactual','recommendation','event'):
                raise ValueError('STEP_NOT_FOUND')
            if db.execute('SELECT 1 FROM annotations WHERE run_id=? AND step_id=?', (request.run_id,request.step_id)).fetchone():
                raise ValueError('ANNOTATION_ALREADY_RECORDED')
            annotation_id=uid('annotation')
            data = dict(request.model_dump(mode='json'), candidate_run_id=root['id'], annotation_id=annotation_id)
            db.execute('INSERT INTO annotations VALUES(?,?,?,?,?)',
                       (annotation_id,request.run_id,request.step_id,request.action,dump(data)))
            self.store.record(request.run_id,'step_annotation',data,annotation_id,db=db)
            challenged = request.action in ('REJECTED','DISPUTED')
            status = 'REVISION_REQUESTED' if challenged and root['status'] in ('REVIEW_PENDING','APPROVED_FOR_INVESTIGATION') else root['status']
            changed = db.execute('UPDATE runs SET status=?,version=version+1 WHERE id=? AND version=?',
                                 (status,root['id'],request.expected_version))
            if changed.rowcount!=1:
                raise ValueError('ANNOTATION_CAS_CONFLICT')
            if challenged:
                self.store.record(root['id'],'trusted_revision',{'cause':annotation_id,'step_run_id':request.run_id,
                    'step_id':request.step_id,'prior_status':root['status'],'status':status,
                    'approval_eligibility_invalidated':True},db=db)
        return {'annotation_id':annotation_id,'candidate_run_id':root['id'],
                'committed_version':request.expected_version+1,'committed':True}
