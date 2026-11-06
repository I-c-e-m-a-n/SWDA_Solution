"""Terminal operator/reviewer interface; no automatic human approval."""
import sqlite3
import argparse
import getpass
import json
from pathlib import Path
from .sources import ROOT
from .store import Store, dump
from .orchestrator import Orchestrator, scenarios
from .evaluation import evaluate
from .approval import ApprovalService
from .schemas import HumanDecision, StepAnnotation


def show(value):
    print(json.dumps(value,ensure_ascii=False,indent=2,default=str))


def main(argv=None):
    parser=argparse.ArgumentParser(description='Hypothetical annex-only simulation; investigation only.')
    parser.add_argument('--db',default=str(ROOT/'runtime/runs.db'))
    parser.add_argument('--reviewers',default=str(ROOT/'config/reviewers.json'))
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('scenarios')
    run=sub.add_parser('run'); run.add_argument('scenario',choices=list(scenarios()))
    sub.add_parser('pending'); sub.add_parser('recover')
    for name in ('history','review','export'):
        p=sub.add_parser(name); p.add_argument('run_id')
        if name=='export': p.add_argument('--output',required=True)
    inspect=sub.add_parser('inspect'); inspect.add_argument('run_id'); inspect.add_argument('step_id')
    step=sub.add_parser('annotate'); step.add_argument('run_id'); step.add_argument('step_id')
    step.add_argument('action',choices=['ACCEPTED','DISPUTED','REJECTED']); step.add_argument('--rationale',required=True)
    step.add_argument('--candidate',required=True,help='Originating candidate ID; verified against persisted lineage')
    step.add_argument('--version',type=int,required=True,help='Current originating candidate version')
    decide=sub.add_parser('decide'); decide.add_argument('run_id')
    decide.add_argument('action',choices=['APPROVE_FOR_INVESTIGATION','REJECT','REQUEST_REVISION'])
    decide.add_argument('--version',type=int,required=True); decide.add_argument('--rationale',required=True)
    ev=sub.add_parser('evaluate'); ev.add_argument('--output')
    demo=sub.add_parser('demo'); demo.add_argument('--output',default=str(ROOT/'runtime/examples'))
    args=parser.parse_args(argv)
    store=Store(args.db)
    try:
        if args.command=='scenarios': show({k:v.model_dump(mode='json') for k,v in scenarios().items()})
        elif args.command=='run':
            result=Orchestrator(store).execute(scenarios()[args.scenario]); show(result['run'])
        elif args.command=='pending':
            with store.connect() as db:
                show([dict(r) for r in db.execute("SELECT id,status,version FROM runs WHERE kind='CANDIDATE' AND status='REVIEW_PENDING'")])
        elif args.command in ('history','export'):
            result=store.export(args.run_id)
            if args.command=='export':
                Path(args.output).parent.mkdir(parents=True,exist_ok=True)
                Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n'); show({'exported':args.output})
            else: show(result)
        elif args.command=='inspect':
            found=[r for r in store.records(args.run_id) if r['id']==args.step_id]
            if not found: raise ValueError('STEP_NOT_FOUND')
            show(found)
        elif args.command=='annotate':
            if input('Record human step annotation? Type YES: ')!='YES': raise ValueError('CANCELLED')
            show(ApprovalService(store,args.reviewers).annotate(StepAnnotation(run_id=args.run_id,step_id=args.step_id,
                action=args.action,rationale=args.rationale,reviewer=getpass.getuser(),origin='human',
                candidate_run_id=args.candidate,expected_version=args.version)))
        elif args.command=='decide':
            show(store.export(args.run_id))
            if input('For further investigation only. Type the exact decision action to commit: ')!=args.action:
                raise ValueError('EXPLICIT_HUMAN_ACTION_REQUIRED')
            show(ApprovalService(store,args.reviewers).decide(HumanDecision(run_id=args.run_id,
                reviewer=getpass.getuser(),origin='human',explicit_action=True,action=args.action,
                rationale=args.rationale,expected_version=args.version)))
        elif args.command=='review':
            review_version=store.run(args.run_id)['version']
            show(store.export(args.run_id))
            action=input('Action (APPROVE_FOR_INVESTIGATION / REJECT / REQUEST_REVISION), or ENTER to leave: ').strip()
            if action:
                rationale=input('Substantive rationale: ')
                if input('Type COMMIT for this human decision: ')!='COMMIT': raise ValueError('CANCELLED')
                show(ApprovalService(store,args.reviewers).decide(HumanDecision(run_id=args.run_id,
                    reviewer=getpass.getuser(),origin='human',explicit_action=True,action=action,
                    rationale=rationale,expected_version=review_version)))
        elif args.command=='recover': show({'incomplete':store.recover()})
        elif args.command=='evaluate':
            result=evaluate(store)
            if args.output:
                Path(args.output).parent.mkdir(parents=True,exist_ok=True)
                Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
            show(result)
            if not result['passed']: return 1
        elif args.command=='demo':
            out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
            index=[]
            for name in ('two_actor','three_role','single_actor','benign_s5','insufficient','new_relative','variation'):
                result=Orchestrator(store).execute(scenarios()[name])
                (out/f'{name}.trace.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
                cards=[r['data'] for r in result['records'] if r['kind']=='card']
                (out/f'{name}.cards.json').write_text(json.dumps(cards,ensure_ascii=False,indent=2)+'\n')
                index.append({'scenario':name,'run_id':result['run']['id'],'status':result['run']['status']})
            # A demonstrable denied operation, never an approval.
            bad=scenarios()['two_actor'].model_copy(update={'fault':'recipient'})
            result=Orchestrator(store).execute(bad,'TEST')
            (out/'denied.trace.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
            report=evaluate(store)
            (out/'evaluation-traces.json').write_text(json.dumps([store.export(r['run_id']) for r in report['results']],ensure_ascii=False,indent=2)+'\n')
            (out/'evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
            (out/'index.json').write_text(json.dumps(index,indent=2)+'\n')
            show({'runs':index,'evaluation_passed':report['passed'],'output':str(out)})
            if not report['passed'] or any(x['status']=='BLOCKED' for x in index): return 1
    except (ValueError,PermissionError,KeyError,OSError,sqlite3.Error,RuntimeError) as exc:
        show({'error':str(exc),'committed_success':False}); return 1
    return 0

if __name__=='__main__':
    raise SystemExit(main())
