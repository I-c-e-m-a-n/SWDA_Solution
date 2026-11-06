import json
import pytest
from swda_part2c.store import Store
from swda_part2c.orchestrator import Orchestrator, scenarios
from swda_part2c.approval import ApprovalService

@pytest.fixture
def store(tmp_path):
    return Store(tmp_path/'test.db')

@pytest.fixture
def sc():
    return scenarios()['two_actor']

@pytest.fixture
def candidate(store,sc):
    result=Orchestrator(store).execute(sc)
    assert result['run']['status']=='REVIEW_PENDING'
    return result

@pytest.fixture
def approval(store,tmp_path):
    path=tmp_path/'reviewers.json'
    path.write_text(json.dumps({'version':'test-local-1','reviewers':['test-human']}))
    return ApprovalService(store,path,current_user=lambda:'test-human')
