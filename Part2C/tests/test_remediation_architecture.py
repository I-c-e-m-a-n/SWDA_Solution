"""Executable component and unchanged source-design checks; not a native render test."""
import hashlib
import json
import re
import pytest
from swda_part2c.models import adapters, ScriptedActor, ScriptedReviewer
from swda_part2c.orchestrator import Orchestrator, scenarios, profiles
from swda_part2c.sources import ROOT
from swda_part2c.schemas import Limits


def test_four_scripts_one_deterministic_orchestrator():
    models=adapters()
    assert set(models)=={'TA','PA','EA','REV'}
    assert all(isinstance(models[a],ScriptedActor) and models[a].actor==a for a in ('TA','PA','EA'))
    assert isinstance(models['REV'],ScriptedReviewer)
    assert not hasattr(Orchestrator,'generate')
    assert set(profiles())==set(models)


def test_extra_autonomous_adapter_is_rejected(store):
    def extra(): return dict(adapters(),PLANNER=ScriptedReviewer())
    result=Orchestrator(store,model_factory=extra).execute(scenarios()['two_actor'])
    assert result['run']['status']=='BLOCKED'
    assert not any(r['kind']=='invocation_started' for r in result['records'])


def test_minimum_card_cap_still_allows_only_one_card(store):
    result=Orchestrator(store,Limits(cards=1)).execute(scenarios()['two_actor'])
    assert result['run']['status']=='REVIEW_PENDING'
    assert sum(r['kind']=='card' for r in result['records'])==1


def test_v3_source_structure_and_render_manifest_remain_consistent():
    directory=ROOT.parent/'Part2A'
    manifest=json.loads((directory/'P2_A_Source_to_Render_Manifest_v3.json').read_text())
    assert len(manifest['outputs'])==15
    for item in manifest['outputs'].values():
        assert hashlib.sha256((directory/item['filename']).read_bytes()).hexdigest()==item['sha256']
    sequence=(directory/'P2_A2_Simulation_Sequence_v3.mmd').read_text()
    assert len(re.findall(r'^\s*(?:participant|actor) \w+ as ',sequence,re.M))==14
    assert len(re.findall(r'PHASE [1-6] ',sequence))==6
    assert len(re.findall(r'^\s*\w+(?:->>|-->>)\w+:',sequence,re.M))==100
    architecture=(directory/'P2_A1_Simulation_Architecture_v3.mmd').read_text()
    assert not re.search(r'^\s*(TA|PA|EA)\s+[-.]+>\s*(TA|PA|EA)\b',architecture,re.M)
    assert 'REV -.->|scoped lookup' in architecture and 'APPROVAL -->|decision record' in architecture
