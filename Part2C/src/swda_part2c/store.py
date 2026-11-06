"""Trusted SQLite writer. Adapters only receive serialised invocation contexts."""
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from .schemas import AuditEvent, Run


def uid(prefix='id'):
    return f'{prefix}-{uuid.uuid4().hex[:16]}'


def dump(value):
    if hasattr(value, 'model_dump'):
        value = value.model_dump(mode='json')
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS runs (
              id TEXT PRIMARY KEY, kind TEXT NOT NULL, parent TEXT REFERENCES runs(id),
              status TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 0, metadata TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS records (
              seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
              run_id TEXT NOT NULL REFERENCES runs(id), kind TEXT NOT NULL, data TEXT NOT NULL,
              timestamp TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
            CREATE TABLE IF NOT EXISTS decisions (
              id TEXT PRIMARY KEY, run_id TEXT UNIQUE NOT NULL REFERENCES runs(id), data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS annotations (
              id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), step_id TEXT NOT NULL,
              action TEXT NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS budgets (
              scope TEXT PRIMARY KEY, used INTEGER NOT NULL DEFAULT 0, cap INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS cf_reservations (
              run_id TEXT PRIMARY KEY REFERENCES runs(id), scope TEXT NOT NULL, remaining INTEGER NOT NULL);
            CREATE TRIGGER IF NOT EXISTS no_record_update BEFORE UPDATE ON records
              BEGIN SELECT RAISE(ABORT, 'append only'); END;
            CREATE TRIGGER IF NOT EXISTS no_record_delete BEFORE DELETE ON records
              BEGIN SELECT RAISE(ABORT, 'append only'); END;
            CREATE TRIGGER IF NOT EXISTS no_decision_update BEFORE UPDATE ON decisions
              BEGIN SELECT RAISE(ABORT, 'append only'); END;
            CREATE TRIGGER IF NOT EXISTS no_decision_delete BEFORE DELETE ON decisions
              BEGIN SELECT RAISE(ABORT, 'append only'); END;
            CREATE TRIGGER IF NOT EXISTS no_annotation_update BEFORE UPDATE ON annotations
              BEGIN SELECT RAISE(ABORT, 'append only'); END;
            CREATE TRIGGER IF NOT EXISTS no_annotation_delete BEFORE DELETE ON annotations
              BEGIN SELECT RAISE(ABORT, 'append only'); END;
            ''')

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        return db

    def create_run(self, run: Run, snapshot=None):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if run.run_type == 'CF':
                parent = db.execute('SELECT * FROM runs WHERE id=?', (run.parent_run_id,)).fetchone()
                if not parent or parent['kind'] != 'CANDIDATE' or parent['status'] != 'RUNNING':
                    raise ValueError('CF_PARENT_INVALID')
                original = json.loads(parent['metadata'])
                if original['scenario'] != run.scenario.model_dump(mode='json'):
                    raise ValueError('CF_PIN_MISMATCH')
                if run.removed_actor not in run.scenario.roles:
                    raise ValueError('CF_REMOVED_ACTOR_INVALID')
                rows = db.execute("SELECT data FROM records WHERE run_id=? AND kind='snapshots'",
                                  (run.parent_run_id,)).fetchall()
                if len(rows) != 1 or snapshot is None:
                    raise ValueError('CF_PARENT_SNAPSHOT_REQUIRED')
                pinned = json.loads(rows[0][0])
                if snapshot != pinned:
                    raise ValueError('CF_RELEASE_PIN_MISMATCH')
                children = [json.loads(r[0]) for r in db.execute(
                    'SELECT metadata FROM runs WHERE parent=?', (run.parent_run_id,))]
                if len(children) >= pinned['limits']['cf']:
                    raise ValueError('CF_BUDGET_EXHAUSTED')
                if any(c['removed_actor'] == run.removed_actor for c in children):
                    raise ValueError('CF_DUPLICATE_REMOVAL')
                participants = {json.loads(r[0])['envelope']['actor'] for r in db.execute(
                    "SELECT data FROM records WHERE run_id=? AND kind='message'", (run.parent_run_id,))}
                if run.removed_actor not in participants:
                    raise ValueError('CF_ACTOR_NOT_PARTICIPATING')
                budget = db.execute('SELECT * FROM budgets WHERE scope=?', (run.parent_run_id,)).fetchone()
                reserved = db.execute('SELECT COALESCE(SUM(remaining),0) FROM cf_reservations WHERE scope=?',
                                      (run.parent_run_id,)).fetchone()[0]
                allocation = run.scenario.rounds * (len(run.scenario.roles) - 1)
                if not budget or budget['cap'] != pinned['limits']['lineage_calls'] or budget['used'] + reserved + allocation > budget['cap']:
                    raise ValueError('CF_CALL_ALLOCATION_EXHAUSTED')
            db.execute('INSERT INTO runs VALUES (?,?,?,?,?,?)',
                       (run.run_id, run.run_type, run.parent_run_id, run.status, run.version, dump(run)))
            self.record(run.run_id, 'run_started', run, db=db)
            if snapshot is not None:
                self.record(run.run_id, 'snapshots', snapshot, db=db)
            if run.run_type == 'CF':
                db.execute('INSERT INTO cf_reservations VALUES(?,?,?)',
                           (run.run_id, run.parent_run_id, allocation))
                self.record(run.run_id, 'cf_admission', {'parent':run.parent_run_id,
                    'removed_actor':run.removed_actor, 'reserved_calls':allocation,
                    'persisted_cap':pinned['limits']['cf']}, db=db)

    def record(self, run_id, kind, data, record_id=None, db=None):
        record_id = record_id or uid(kind)
        if db is not None:
            db.execute('INSERT INTO records(id,run_id,kind,data) VALUES(?,?,?,?)',
                       (record_id, run_id, kind, dump(data)))
        else:
            with self.connect() as connection:
                self.record(run_id, kind, data, record_id, connection)
        return record_id

    def event(self, run_id, kind, data, actor='ORCH'):
        event = AuditEvent(event_id=uid('event'), timestamp=datetime.now(timezone.utc).isoformat(),
                           run_id=run_id, trace_id=run_id, kind=kind, actor=actor, payload=data)
        return self.record(run_id, 'event', event, event.event_id)

    def run(self, run_id):
        with self.connect() as db:
            row = db.execute('SELECT * FROM runs WHERE id=?', (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        return dict(row)

    def records(self, run_id, kind=None):
        sql = 'SELECT * FROM records WHERE run_id=?'
        args = [run_id]
        if kind:
            sql += ' AND kind=?'
            args.append(kind)
        with self.connect() as db:
            return [dict(r, data=json.loads(r['data'])) for r in db.execute(sql+' ORDER BY seq', args)]

    def finish(self, run_id, status):
        # Only orchestration owns RUNNING transitions. Approval has a separate CAS transaction.
        with self.connect() as db:
            cur = db.execute("UPDATE runs SET status=?, version=version+1 WHERE id=? AND status='RUNNING'",
                             (status, run_id))
            if cur.rowcount != 1:
                raise ValueError('STATE_CONFLICT')
            self.record(run_id, 'state_transition', {'status': status}, db=db)
            db.execute('UPDATE cf_reservations SET remaining=0 WHERE run_id=?', (run_id,))

    def budget(self, scope, cap):
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO budgets VALUES (?,0,?)', (scope, cap))
            if db.execute('SELECT cap FROM budgets WHERE scope=?', (scope,)).fetchone()[0] != cap:
                raise ValueError('BUDGET_CAP_CHANGED')

    def consume(self, scopes, *, run_id=None, invocation=None, usage=None):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            for scope in scopes:
                reserved = db.execute('SELECT COALESCE(SUM(remaining),0) FROM cf_reservations WHERE scope=? AND run_id!=?',
                                      (scope, run_id or '')).fetchone()[0]
                cur = db.execute('UPDATE budgets SET used=used+1 WHERE scope=? AND used+? < cap', (scope, reserved))
                if cur.rowcount != 1:
                    raise ValueError('CALL_BUDGET_EXHAUSTED')
            if run_id:
                db.execute('UPDATE cf_reservations SET remaining=MAX(0,remaining-1) WHERE run_id=?', (run_id,))
            if invocation:
                self.record(run_id, 'invocation_started', invocation, db=db)
                self.record(run_id, 'usage', usage, db=db)

    def usage(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT * FROM budgets ORDER BY scope')]

    def usage_for(self, run_id):
        """Only this run's local, aggregate and suite scopes; no unrelated experiments."""
        scopes = {run_id, self.run(run_id)['parent']}
        with self.connect() as db:
            scopes.update(r[0] for r in db.execute('SELECT id FROM runs WHERE parent=?', (run_id,)))
        for record in self.records(run_id, 'usage'):
            scopes.update(record['data']['scopes'])
        return [b for b in self.usage() if b['scope'] in scopes]

    def recover(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            ids = [r[0] for r in db.execute("SELECT id FROM runs WHERE status='RUNNING'")]
            for run_id in ids:
                starts = [json.loads(r[0]) for r in db.execute(
                    "SELECT data FROM records WHERE run_id=? AND kind='invocation_started'", (run_id,))]
                ends = {json.loads(r[0])['invocation_id'] for r in db.execute(
                    "SELECT data FROM records WHERE run_id=? AND kind='invocation'", (run_id,))}
                for started in starts:
                    if started['invocation_id'] not in ends:
                        self.record(run_id, 'invocation', dict(started, raw_output='', outcome='INTERRUPTED',
                            error_code='PROCESS_INTERRUPTED'), started['invocation_id'], db=db)
                db.execute("UPDATE runs SET status='INCOMPLETE',version=version+1 WHERE id=?", (run_id,))
                db.execute('UPDATE cf_reservations SET remaining=0 WHERE run_id=?', (run_id,))
                self.record(run_id, 'recovery', {'reason': 'interrupted_execution'}, db=db)
        return ids

    def export(self, run_id):
        with self.connect() as db:
            children = [r[0] for r in db.execute('SELECT id FROM runs WHERE parent=? ORDER BY id', (run_id,))]
            decisions = [json.loads(r[0]) for r in db.execute('SELECT data FROM decisions WHERE run_id=?', (run_id,))]
            annotations = [json.loads(r[0]) for r in db.execute('SELECT data FROM annotations WHERE run_id=?', (run_id,))]
        return {'run': self.run(run_id), 'records': self.records(run_id), 'budgets': self.usage_for(run_id),
                'decisions': decisions, 'annotations': annotations,
                'children': [self.export(c) for c in children]}
