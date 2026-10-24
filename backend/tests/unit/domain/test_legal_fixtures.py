"""Parametrised runner for counsel-readable legal fixtures (T2.7).

Each TOML file under tests/fixtures/legal/ declares a module, a rule-set version and a
`reviewed_by` status. Only fields listed in a case's `expected` table are compared.
"""

import tomllib
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from app.domain.deemed_clock import BuyerResponseFact, CaseFacts, compute_clock
from app.domain.interest import BankRatePeriod, PaymentFact, compute_interest
from app.domain.rules import RuleSet
from app.domain.types import DealType, ResponseChannel, ResponseKind

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "legal"


def _load(name: str) -> dict[str, Any]:
    with (FIXTURE_DIR / name).open("rb") as handle:
        return tomllib.load(handle)


CLOCK = _load("deemed_clock.toml")
INTEREST = _load("interest.toml")


@pytest.mark.parametrize("document", [CLOCK, INTEREST], ids=["deemed_clock", "interest"])
def test_fixture_files_declare_review_status(document: dict[str, Any]) -> None:
    meta = document["meta"]
    assert meta["rule_set"] == "msmed-v1"
    assert meta["reviewed_by"], "reviewed_by must be recorded ('pending' until counsel signs)"
    ids = [case["id"] for case in document["case"]]
    assert len(ids) == len(set(ids)), "fixture IDs must be unique"
    for case in document["case"]:
        assert case["title"] and case["expected"], case["id"]


@pytest.mark.parametrize("case", CLOCK["case"], ids=[c["id"] for c in CLOCK["case"]])
def test_deemed_clock_fixture(case: dict[str, Any], rule_set: RuleSet) -> None:
    raw = case["input"]
    facts = CaseFacts(
        delivery_date=raw["delivery_date"],
        deal_type=DealType(raw["deal_type"]),
        agreed_payment_days=raw.get("agreed_payment_days"),
        agreed_due_date=raw.get("agreed_due_date"),
        responses=tuple(
            BuyerResponseFact(
                kind=ResponseKind(r["kind"]),
                received_on=r["received_on"],
                channel=ResponseChannel(r["channel"]),
                objection_removed_on=r.get("objection_removed_on"),
            )
            for r in raw.get("responses", [])
        ),
    )
    result = compute_clock(facts, raw["today"], rule_set)

    for field, expected in case["expected"].items():
        actual = getattr(result, field)
        if expected == "none":
            assert actual is None, f"{case['id']}.{field}"
        elif isinstance(expected, (date, bool, int)):
            assert actual == expected, f"{case['id']}.{field}"
        else:
            assert actual is not None and actual.value == expected, f"{case['id']}.{field}"


@pytest.mark.parametrize("case", INTEREST["case"], ids=[c["id"] for c in INTEREST["case"]])
def test_interest_fixture(case: dict[str, Any], rule_set: RuleSet) -> None:
    raw = case["input"]
    result = compute_interest(
        principal=Decimal(raw["principal"]),
        interest_start=raw["interest_start"],
        as_of=raw["as_of"],
        payments=[
            PaymentFact(Decimal(p["amount"]), p["received_on"]) for p in raw.get("payments", [])
        ],
        rate_table=[
            BankRatePeriod(r["effective_from"], Decimal(r["rate_percent"]), r["source"], False)
            for r in raw["rates"]
        ],
        rule_set=rule_set,
    )

    for field, expected in case["expected"].items():
        if field == "periods":
            assert len(result.periods) == expected, case["id"]
        else:
            assert getattr(result, field) == Decimal(expected), f"{case['id']}.{field}"
    assert result.uses_unverified_rates or not result.periods
