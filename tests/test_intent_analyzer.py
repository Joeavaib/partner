import pytest
from src.ml.intent_analyzer import IntentAnalyzer

@pytest.fixture
def analyzer():
    return IntentAnalyzer()

def test_bug_fixing_intent(analyzer):
    result = analyzer.analyze("Fix the broken login function in auth.py")
    assert result['intent'] == 'bug_fixing'
    assert 'auth.py' in result['entities']
    assert 'error_logs' in result['context_needs']

def test_optimization_intent(analyzer):
    result = analyzer.analyze("Make the database query faster in db_client.py")
    assert result['intent'] == 'code_optimization'
    assert 'db_client.py' in result['entities']
    assert 'benchmarks' in result['context_needs']

def test_refactoring_intent(analyzer):
    result = analyzer.analyze("Refactor the messy code in service.py to be more readable")
    assert result['intent'] == 'refactoring'
    assert 'service.py' in result['entities']

def test_code_generation_intent(analyzer):
    result = analyzer.analyze("Create a new FastAPI endpoint for user registration")
    assert result['intent'] == 'code_generation'

def test_entity_extraction(analyzer):
    result = analyzer.analyze("Update the handle_request() function in /src/app.py")
    assert 'handle_request()' in result['entities']
    assert '/src/app.py' in result['entities']

def test_general_fallback(analyzer):
    result = analyzer.analyze("Hello there, how are you today?")
    assert result['intent'] == 'general'
    assert result['confidence'] <= 0.5
