import copy
import tomllib
from datetime import date
from importlib.resources import files
from typing import Any

import pytest

from app.domain.errors import DomainValidationError, RuleSetError
from app.domain.rules import RuleSet, Tier, VerificationStatus, parse_rule_set
from app.rules.loader import load_rule_set


def _document() -> dict[str, Any]:
    text = files("app.rules").joinpath("msmed-v1.toml").read_text(encoding="utf-8")
    return tomllib.loads(text)


def test_packaged_rule_set_loads_with_expected_parameters(rule_set: RuleSet) -> None:
    params = rule_set.parameters
    assert rule_set.version == "msmed-v1"
    assert params.objection_window_days == 15
    assert params.appointed_day_period_days == 15
    assert params.max_agreed_payment_days == 45
    assert str(params.interest_multiplier) == "3"
    assert params.limitation_years == 3


def test_every_rule_carries_source_effective_date_and_status(rule_set: RuleSet) -> None:
    for rule in rule_set.rules:
        assert rule.source and rule.explanation and rule.title
        assert isinstance(rule.effective_from, date)
        assert rule.decision_refs


def test_statute_rules_are_text_checked_and_nothing_is_counsel_confirmed(
    rule_set: RuleSet,
) -> None:
    statute = [r for r in rule_set.rules if r.tier is Tier.STATUTE]
    assert {r.rule_id for r in statute} == {
        "R1",
        "R2",
        "R3",
        "R4",
        "R5",
        "R6",
        "R7",
        "R8",
        "R9",
        "R13",
    }
    assert all(r.verification_status is VerificationStatus.TEXT_CHECKED for r in statute)
    assert not any(r.counsel_confirmed for r in rule_set.rules)


def test_d3_to_d5_assumptions_are_provisional_defaults(rule_set: RuleSet) -> None:
    for rule_id in ("A1", "A2", "A3", "A4", "A10"):
        assert rule_set.rule(rule_id).verification_status is VerificationStatus.PROVISIONAL_DEFAULT


def test_2026_amendment_is_flagged_as_pending_review(rule_set: RuleSet) -> None:
    # Act 16 of 2026: ss.2(b), 15, 16 unchanged, but enactment text, s.8 (supplier status)
    # and TReDS payment dates remain open questions that must surface on every output.
    assert {"LR-21", "LR-23", "LR-24"} <= set(rule_set.pending_reviews)
    assert "Act 16 of 2026" in rule_set.legal_basis
    assert "LR-23" in rule_set.rule("R9").decision_refs
    assert "LR-24" in rule_set.rule("R8").decision_refs
    assert "LR-25" in rule_set.rule("R13").decision_refs


def test_amendment_review_did_not_change_statutory_periods(rule_set: RuleSet) -> None:
    # The Amendment Act does not amend ss.2(b), 15 or 16, so these values must not move.
    params = rule_set.parameters
    assert (params.objection_window_days, params.appointed_day_period_days) == (15, 15)
    assert params.max_agreed_payment_days == 45
    assert str(params.interest_multiplier) == "3"


def test_unconfirmed_returns_ids_in_order_without_duplicates(rule_set: RuleSet) -> None:
    assert rule_set.unconfirmed(["R3", "A1", "R3"]) == ("R3", "A1")


def test_unknown_rule_id_raises(rule_set: RuleSet) -> None:
    with pytest.raises(RuleSetError):
        rule_set.rule("R999")


def test_rule_set_rejects_deliveries_before_its_effective_date(rule_set: RuleSet) -> None:
    with pytest.raises(DomainValidationError):
        rule_set.check_applies_to(date(2006, 10, 1))
    rule_set.check_applies_to(date(2006, 10, 2))


def test_effective_until_bounds_the_rule_set() -> None:
    doc = _document()
    doc["rule_set"]["effective_until"] = date(2027, 1, 1)
    bounded = parse_rule_set(doc)
    bounded.check_applies_to(date(2026, 12, 31))
    with pytest.raises(DomainValidationError):
        bounded.check_applies_to(date(2027, 1, 1))


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda d: d.update(extra={}), "unknown keys"),
        (lambda d: d["rule_set"].update(surprise=1), "unknown keys"),
        (lambda d: d["parameters"].pop("objection_window_days"), "missing keys"),
        (lambda d: d["parameters"].update(objection_window_days=0), "integer in"),
        (lambda d: d["parameters"].update(objection_window_days=True), "integer in"),
        (lambda d: d["parameters"].update(acknowledgement_ends_window="no"), "true or false"),
        (lambda d: d["parameters"].update(holiday_adjustment=True), "not supported"),
        (lambda d: d["parameters"].update(payment_allocation="interest_first"), "not supported"),
        (lambda d: d["parameters"].update(interest_multiplier=3), "decimal string"),
        (lambda d: d["parameters"].update(interest_multiplier="three"), "valid decimal"),
        (lambda d: d["parameters"].update(interest_multiplier="-1"), "positive decimal"),
        (lambda d: d["rules"].append(copy.deepcopy(d["rules"][0])), "Duplicate rule IDs"),
        (lambda d: d["rules"][0].update(tier="X"), "not a valid Tier"),
        (lambda d: d["rules"][0].update(verification_status="provisional_default"), "statute"),
        (lambda d: d["rules"][-1].update(verification_status="text_checked"), "statute-text"),
        (lambda d: d["rules"][0].update(source=""), "non-empty string"),
        (lambda d: d["rules"][0].update(decision_refs="LR-01"), "list of non-empty"),
        (lambda d: d["rules"][0].update(effective_from="2006-10-02"), "local date"),
        (lambda d: d.update(rules=[]), "non-empty list"),
        (lambda d: d.update(parameters=[]), "must be a table"),
        (lambda d: d["rule_set"].update(effective_until=date(2000, 1, 1)), "after effective_from"),
    ],
)
def test_invalid_documents_are_rejected(mutate: Any, message: str) -> None:
    doc = _document()
    mutate(doc)
    with pytest.raises(RuleSetError, match=message):
        parse_rule_set(doc)


@pytest.mark.parametrize("version", ["msmed", "../secrets", "msmed-v1.toml", "msmed-v99"])
def test_loader_rejects_bad_or_unknown_versions(version: str) -> None:
    with pytest.raises(RuleSetError):
        load_rule_set(version)
