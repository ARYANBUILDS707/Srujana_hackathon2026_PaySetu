import pytest

from app.domain.rules import RuleSet
from app.rules.loader import load_rule_set


@pytest.fixture(scope="session")
def rule_set() -> RuleSet:
    return load_rule_set("msmed-v1")
