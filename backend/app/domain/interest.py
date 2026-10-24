"""Delayed-payment interest under MSMED Act s.16 (T2.3).

Statute (R8): compound interest with monthly rests at three times the RBI bank rate.
Method (provisional simulation defaults approved by the owner, NOT validated legal rules;
LR-12 to LR-14):

- A1: a complete monthly period accrues balance × annual rate ÷ 12; a period cut short by the
  as-of date, or split by a payment, accrues each segment at balance × annual rate × days ÷ 365.
- A2: interest is rounded half-up to the paisa at the end of each period (each monthly rest).
- A3: each period uses multiplier × the bank rate in force on the period's first day.
- A4: payments reduce principal first, then capitalised interest; any excess is a credit that
  offsets later interest.
- A10: interest accrues for every day from `interest_start` through `as_of` inclusive; a payment
  reduces the balance from its own date.

Monthly periods are anchored on the interest start date (period k runs from
start + k months to start + k+1 months, exclusive), with month-end clamping.

The rate table is an input. The engine never supplies a bank rate itself; each period records
whether its rate came from a verified source.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from app.domain.dates import add_months
from app.domain.errors import DomainValidationError, MissingRateError
from app.domain.rules import RuleSet

PAISA = Decimal("0.01")
ZERO = Decimal("0.00")
HUNDRED = Decimal(100)
MAX_BANK_RATE_PERCENT = Decimal(50)
MAX_AMOUNT = Decimal("10000000000.00")  # Rs 1,000 crore (API.md Section 3)
_RULES_APPLIED = ("R7", "R8", "A1", "A2", "A3", "A4", "A10")


@dataclass(frozen=True)
class BankRatePeriod:
    """RBI bank rate in force from `effective_from` until the next period starts."""

    effective_from: date
    rate_percent: Decimal
    source: str
    verified: bool
    verified_by: str | None = None


@dataclass(frozen=True)
class PaymentFact:
    amount: Decimal
    received_on: date
    payment_id: str | None = None


class PeriodKind(StrEnum):
    FULL_MONTH = "full_month"
    PRO_RATA = "pro_rata"


@dataclass(frozen=True)
class InterestPeriod:
    start: date
    end: date  # inclusive
    days: int
    kind: PeriodKind
    is_rest: bool  # True when the period ends on a monthly rest (interest capitalised)
    bank_rate_percent: Decimal
    annual_rate_percent: Decimal
    rate_verified: bool
    opening_balance: Decimal
    interest: Decimal
    payments: Decimal
    closing_principal: Decimal
    closing_interest: Decimal


@dataclass(frozen=True)
class InterestResult:
    as_of: date
    interest_start: date
    principal: Decimal
    total_paid: Decimal
    paid_to_principal: Decimal
    paid_to_interest: Decimal
    unapplied_credit: Decimal
    outstanding_principal: Decimal
    interest_accrued: Decimal
    interest_outstanding: Decimal
    total_outstanding: Decimal
    periods: tuple[InterestPeriod, ...]
    uses_unverified_rates: bool
    rule_set_version: str
    rules_applied: tuple[str, ...]
    unconfirmed_rules: tuple[str, ...]
    pending_reviews: tuple[str, ...]

    @property
    def is_principal_settled(self) -> bool:
        return self.outstanding_principal == ZERO


@dataclass
class _Ledger:
    principal: Decimal
    interest: Decimal = ZERO
    credit: Decimal = ZERO
    paid_to_principal: Decimal = ZERO
    paid_to_interest: Decimal = ZERO

    @property
    def balance(self) -> Decimal:
        return self.principal + self.interest

    def apply_payment(self, amount: Decimal) -> None:
        """A4: principal first, then capitalised interest, then credit."""
        to_principal = min(amount, self.principal)
        self.principal -= to_principal
        self.paid_to_principal += to_principal
        remaining = amount - to_principal
        to_interest = min(remaining, self.interest)
        self.interest -= to_interest
        self.paid_to_interest += to_interest
        self.credit += remaining - to_interest

    def add_interest(self, amount: Decimal) -> None:
        offset = min(self.credit, amount)
        self.credit -= offset
        self.paid_to_interest += offset
        self.interest += amount - offset


def compute_interest(
    *,
    principal: Decimal,
    interest_start: date,
    as_of: date,
    payments: Sequence[PaymentFact],
    rate_table: Sequence[BankRatePeriod],
    rule_set: RuleSet,
) -> InterestResult:
    """Compute illustrative s.16 interest from `interest_start` through `as_of` (inclusive).

    Payments dated after `as_of` are ignored. If `as_of` is before `interest_start`, no interest
    has accrued and the period table is empty.
    """
    _validate_money("principal", principal)
    for i, payment in enumerate(payments):
        _validate_money(f"payments[{i}].amount", payment.amount)
    rates = _validated_rates(rate_table)
    params = rule_set.parameters

    counted = sorted((p for p in payments if p.received_on <= as_of), key=lambda p: p.received_on)
    ledger = _Ledger(principal=principal)
    pending = list(counted)
    while pending and pending[0].received_on < interest_start:
        ledger.apply_payment(pending.pop(0).amount)

    periods: list[InterestPeriod] = []
    stop = as_of + timedelta(days=1)  # accrual is half-open: [start, stop)
    k = 0
    while (period_start := add_months(interest_start, k)) < stop:
        period_end = add_months(interest_start, k + 1)
        accrual_end = min(period_end, stop)
        bank_rate, verified = _rate_on(period_start, rates)
        annual = bank_rate * params.interest_multiplier
        opening_balance = ledger.balance

        in_period = []
        while pending and pending[0].received_on < accrual_end:
            in_period.append(pending.pop(0))
        paid = sum((p.amount for p in in_period), ZERO)

        if accrual_end == period_end and not in_period:
            kind = PeriodKind.FULL_MONTH
            raw = opening_balance * annual / HUNDRED / params.months_per_year
        else:
            kind = PeriodKind.PRO_RATA
            raw = Decimal(0)
            segment_start = period_start
            for payment in in_period:
                raw += _pro_rata(
                    ledger.balance,
                    annual,
                    segment_start,
                    payment.received_on,
                    params.day_count_basis_days,
                )
                ledger.apply_payment(payment.amount)
                segment_start = payment.received_on
            raw += _pro_rata(
                ledger.balance, annual, segment_start, accrual_end, params.day_count_basis_days
            )

        interest = raw.quantize(PAISA, rounding=ROUND_HALF_UP)
        ledger.add_interest(interest)
        periods.append(
            InterestPeriod(
                start=period_start,
                end=accrual_end - timedelta(days=1),
                days=(accrual_end - period_start).days,
                kind=kind,
                is_rest=accrual_end == period_end,
                bank_rate_percent=bank_rate,
                annual_rate_percent=annual,
                rate_verified=verified,
                opening_balance=opening_balance,
                interest=interest,
                payments=paid,
                closing_principal=ledger.principal,
                closing_interest=ledger.interest,
            )
        )
        k += 1

    accrued = sum((p.interest for p in periods), ZERO)
    total_paid = sum((p.amount for p in counted), ZERO)
    return InterestResult(
        as_of=as_of,
        interest_start=interest_start,
        principal=principal,
        total_paid=total_paid,
        paid_to_principal=ledger.paid_to_principal,
        paid_to_interest=ledger.paid_to_interest,
        unapplied_credit=ledger.credit,
        outstanding_principal=ledger.principal,
        interest_accrued=accrued,
        interest_outstanding=ledger.interest,
        total_outstanding=ledger.balance,
        periods=tuple(periods),
        uses_unverified_rates=any(not p.rate_verified for p in periods),
        rule_set_version=rule_set.version,
        rules_applied=_RULES_APPLIED,
        unconfirmed_rules=rule_set.unconfirmed(_RULES_APPLIED),
        pending_reviews=rule_set.pending_reviews,
    )


def _pro_rata(balance: Decimal, annual: Decimal, start: date, end: date, basis: int) -> Decimal:
    days = (end - start).days
    return balance * annual / HUNDRED * Decimal(days) / Decimal(basis)


def _rate_on(day: date, rates: Sequence[BankRatePeriod]) -> tuple[Decimal, bool]:
    """Bank rate in force on `day` (A3). No fallback: a gap raises `MissingRateError`."""
    applicable = [r for r in rates if r.effective_from <= day]
    if not applicable:
        raise MissingRateError(f"No bank rate is recorded in force on {day.isoformat()}.")
    current = applicable[-1]
    return current.rate_percent, current.verified


def _validated_rates(rate_table: Sequence[BankRatePeriod]) -> tuple[BankRatePeriod, ...]:
    rates = tuple(sorted(rate_table, key=lambda r: r.effective_from))
    seen: set[date] = set()
    for rate in rates:
        if rate.effective_from in seen:
            raise DomainValidationError(
                f"Duplicate bank rate for {rate.effective_from.isoformat()}."
            )
        seen.add(rate.effective_from)
        value = rate.rate_percent
        if not isinstance(value, Decimal) or not value.is_finite():
            raise DomainValidationError("Bank rates must be finite Decimal values.")
        if not ZERO < value <= MAX_BANK_RATE_PERCENT:
            raise DomainValidationError("Bank rates must be above 0% and at most 50%.")
        if not rate.source.strip():
            raise DomainValidationError("Every bank rate needs a source.")
        if rate.verified and not (rate.verified_by and rate.verified_by.strip()):
            raise DomainValidationError("A verified bank rate must record who verified it.")
    return rates


def _validate_money(name: str, value: Decimal) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise DomainValidationError(f"{name} must be a finite Decimal.")
    exponent = value.as_tuple().exponent
    if isinstance(exponent, int) and exponent < -2:
        raise DomainValidationError(f"{name} must have at most two decimal places.")
    if not ZERO < value <= MAX_AMOUNT:
        raise DomainValidationError(f"{name} must be greater than 0 and at most {MAX_AMOUNT}.")
