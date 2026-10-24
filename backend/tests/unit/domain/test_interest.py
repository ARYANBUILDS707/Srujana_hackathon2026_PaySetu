"""Interest engine unit tests beyond the legal fixtures.

Reference figures test arithmetic consistency under the provisional defaults A1–A4 and A10.
They do not establish statutory correctness (LR-12 to LR-14).
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.domain.errors import DomainValidationError, MissingRateError
from app.domain.interest import (
    BankRatePeriod,
    InterestResult,
    PaymentFact,
    PeriodKind,
    compute_interest,
)
from app.domain.rules import RuleSet

START = date(2026, 11, 17)
FIXTURE_RATE = BankRatePeriod(date(2026, 10, 7), Decimal("5.75"), "Fixture value", False)


def _run(
    rule_set: RuleSet,
    *,
    principal: str = "500000.00",
    as_of: date = date(2027, 11, 16),
    start: date = START,
    payments: tuple[PaymentFact, ...] = (),
    rates: tuple[BankRatePeriod, ...] = (FIXTURE_RATE,),
) -> InterestResult:
    return compute_interest(
        principal=Decimal(principal),
        interest_start=start,
        as_of=as_of,
        payments=payments,
        rate_table=rates,
        rule_set=rule_set,
    )


def test_reference_calculation_93406_72(rule_set: RuleSet) -> None:
    result = _run(rule_set)
    assert result.interest_accrued == Decimal("93406.72")
    assert result.total_outstanding == Decimal("593406.72")
    assert all(p.kind is PeriodKind.FULL_MONTH and p.is_rest for p in result.periods)
    assert result.periods[0].annual_rate_percent == Decimal("17.25")
    assert result.uses_unverified_rates
    assert "LR-21" in result.pending_reviews
    assert {"A1", "A2", "A3", "A4", "A10"} <= set(result.unconfirmed_rules)


def test_as_of_before_interest_start_accrues_nothing(rule_set: RuleSet) -> None:
    result = _run(rule_set, as_of=START - timedelta(days=1))
    assert result.periods == () and result.interest_accrued == Decimal("0.00")


def test_interest_on_the_start_day_counts_one_day(rule_set: RuleSet) -> None:
    result = _run(rule_set, principal="365000.00", as_of=START)
    # 365000 × 17.25% × 1/365 = 172.50
    assert result.interest_accrued == Decimal("172.50")
    assert result.periods[0].days == 1 and not result.periods[0].is_rest


def test_interest_never_decreases_as_the_as_of_date_moves_forward(rule_set: RuleSet) -> None:
    rates = (
        BankRatePeriod(date(2026, 1, 1), Decimal("5.50"), "Hypothetical", False),
        BankRatePeriod(date(2027, 3, 1), Decimal("6.25"), "Hypothetical", False),
    )
    previous = Decimal("0.00")
    for offset in range(0, 450):
        current = _run(rule_set, as_of=START + timedelta(days=offset), rates=rates).interest_accrued
        assert current >= previous, f"interest fell on day {offset}"
        previous = current


def test_month_end_anchoring_through_a_leap_february(rule_set: RuleSet) -> None:
    result = _run(rule_set, start=date(2028, 1, 31), as_of=date(2028, 4, 29))
    starts = [p.start for p in result.periods]
    assert starts == [date(2028, 1, 31), date(2028, 2, 29), date(2028, 3, 31)]
    assert [p.days for p in result.periods[:2]] == [29, 31]


def test_payment_after_as_of_is_ignored(rule_set: RuleSet) -> None:
    later = PaymentFact(Decimal("1000.00"), date(2028, 1, 1))
    result = _run(rule_set, payments=(later,))
    assert result.total_paid == Decimal("0.00")
    assert result.interest_accrued == Decimal("93406.72")


def test_overpayment_becomes_credit_that_offsets_later_interest(rule_set: RuleSet) -> None:
    # Pays principal plus 100.00 on the start day; later interest is absorbed by the credit.
    payment = PaymentFact(Decimal("100100.00"), START)
    result = _run(
        rule_set, principal="100000.00", payments=(payment,), as_of=START + timedelta(days=40)
    )
    assert result.outstanding_principal == Decimal("0.00")
    assert result.interest_accrued == Decimal("0.00")
    assert result.unapplied_credit == Decimal("100.00")
    assert result.is_principal_settled


def test_payment_beyond_principal_pays_capitalised_interest(rule_set: RuleSet) -> None:
    # After one full month, 1437.50 interest is capitalised; pay 100000 + 437.50 later.
    payment = PaymentFact(Decimal("100437.50"), date(2026, 12, 17))
    result = _run(rule_set, principal="100000.00", payments=(payment,), as_of=date(2026, 12, 17))
    assert result.paid_to_principal == Decimal("100000.00")
    assert result.paid_to_interest == Decimal("437.50")
    # 1000.00 capitalised interest remains, plus one day (17 Dec, inclusive per A10) on it:
    # 1000.00 × 17.25% × 1/365 = 0.4726 → 0.47.
    assert result.interest_outstanding == Decimal("1000.47")


def test_verified_rates_are_reported_as_verified(rule_set: RuleSet) -> None:
    verified = BankRatePeriod(
        date(2026, 10, 7), Decimal("5.75"), "RBI press release", True, "Reviewer"
    )
    assert not _run(rule_set, rates=(verified,)).uses_unverified_rates


def test_missing_rate_for_a_period_raises_instead_of_guessing(rule_set: RuleSet) -> None:
    late_rate = BankRatePeriod(date(2027, 1, 1), Decimal("5.75"), "Fixture", False)
    with pytest.raises(MissingRateError):
        _run(rule_set, rates=(late_rate,))
    with pytest.raises(MissingRateError):
        _run(rule_set, rates=())


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"principal": "0.00"}, "greater than 0"),
        ({"principal": "-5.00"}, "greater than 0"),
        ({"principal": "100.001"}, "two decimal places"),
        ({"principal": "10000000000.01"}, "at most"),
        ({"principal": "NaN"}, "finite"),
        ({"payments": (PaymentFact(Decimal("0"), START),)}, "greater than 0"),
        (
            {"rates": (FIXTURE_RATE, BankRatePeriod(date(2026, 10, 7), Decimal("6"), "x", False))},
            "Duplicate",
        ),
        ({"rates": (BankRatePeriod(date(2026, 1, 1), Decimal("0"), "x", False),)}, "above 0%"),
        ({"rates": (BankRatePeriod(date(2026, 1, 1), Decimal("NaN"), "x", False),)}, "finite"),
        ({"rates": (BankRatePeriod(date(2026, 1, 1), Decimal("51"), "x", False),)}, "at most 50%"),
        ({"rates": (BankRatePeriod(date(2026, 1, 1), Decimal("5"), " ", False),)}, "source"),
        ({"rates": (BankRatePeriod(date(2026, 1, 1), Decimal("5"), "x", True),)}, "who verified"),
    ],
)
def test_invalid_inputs_are_rejected(
    kwargs: dict[str, object], message: str, rule_set: RuleSet
) -> None:
    with pytest.raises(DomainValidationError, match=message):
        _run(rule_set, **kwargs)  # type: ignore[arg-type]


def test_float_money_is_rejected(rule_set: RuleSet) -> None:
    with pytest.raises(DomainValidationError, match="finite Decimal"):
        compute_interest(
            principal=500000.0,  # type: ignore[arg-type]
            interest_start=START,
            as_of=START,
            payments=(),
            rate_table=(FIXTURE_RATE,),
            rule_set=rule_set,
        )
