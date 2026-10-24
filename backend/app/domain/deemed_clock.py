"""DeemedClock: acceptance, due date and interest start for one delivery (T2.2).

Rule IDs refer to PRD Section 4 and `app/rules/msmed-v1.toml`. The result is computed from
stored facts plus `today` on every call (ADR-006); nothing here is persisted.

Day numbering: Day 0 is the delivery date, and the objection window ends on Day N where
N = `objection_window_days` (R4a).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

from app.domain.dates import add_years_feb28
from app.domain.errors import DomainValidationError
from app.domain.rules import RuleSet
from app.domain.types import DealType, ResponseChannel, ResponseKind

MAX_AGREED_PAYMENT_DAYS_INPUT = 365


class AcceptanceState(StrEnum):
    WINDOW_OPEN = "window_open"
    OBJECTION_RAISED = "objection_raised"
    ACCEPTED = "accepted"


class AcceptanceBasis(StrEnum):
    DEEMED = "deemed"
    ACKNOWLEDGED = "acknowledged"
    OBJECTION_REMOVED = "objection_removed"


class PaymentState(StrEnum):
    NOT_DUE = "not_due"
    OVERDUE = "overdue"
    SETTLED = "settled"


@dataclass(frozen=True)
class BuyerResponseFact:
    kind: ResponseKind
    received_on: date
    channel: ResponseChannel
    objection_removed_on: date | None = None
    response_id: str | None = None


@dataclass(frozen=True)
class CaseFacts:
    delivery_date: date
    deal_type: DealType
    agreed_payment_days: int | None = None
    agreed_due_date: date | None = None
    responses: tuple[BuyerResponseFact, ...] = ()


@dataclass(frozen=True)
class ResponseAssessment:
    index: int
    response_id: str | None
    kind: ResponseKind
    received_on: date
    within_window: bool
    counts_as_written: bool
    affects_acceptance: bool
    rule_ids: tuple[str, ...]
    note: str


@dataclass(frozen=True)
class Explanation:
    field: str
    rule_ids: tuple[str, ...]
    text: str


@dataclass(frozen=True)
class ClockResult:
    as_of: date
    rule_set_version: str
    acceptance_state: AcceptanceState
    acceptance_basis: AcceptanceBasis | None
    window_end: date
    window_day: int | None
    window_days_remaining: int | None
    acceptance_date: date | None
    appointed_day: date | None
    due_date: date | None
    interest_start: date | None
    indicative_limitation_date: date | None
    payment_state: PaymentState | None
    days_overdue: int | None
    terms_capped_at_max: bool
    responses: tuple[ResponseAssessment, ...]
    explanations: tuple[Explanation, ...]
    rules_applied: tuple[str, ...]
    unconfirmed_rules: tuple[str, ...]
    pending_reviews: tuple[str, ...]


def compute_clock(
    facts: CaseFacts, today: date, rule_set: RuleSet, *, is_settled: bool = False
) -> ClockResult:
    """Compute the DeemedClock for one case as of `today` (an Asia/Kolkata calendar date).

    `is_settled` is True when the outstanding principal is zero (computed by the caller from
    payments). Raises `DomainValidationError` for inconsistent or out-of-range facts.
    """
    _validate(facts, today, rule_set)
    params = rule_set.parameters
    applied: list[str] = ["A5", "A8", "R4a", "R4b"]
    explanations: list[Explanation] = []

    window_end = facts.delivery_date + timedelta(days=params.objection_window_days)
    window_closed = today > window_end
    explanations.append(
        Explanation(
            "window_end",
            ("R2", "R3", "R4a"),
            f"The buyer can object in writing until Day {params.objection_window_days} "
            f"({window_end.isoformat()}).",
        )
    )

    assessments = tuple(_assess(i, r, window_end, rule_set) for i, r in enumerate(facts.responses))
    for assessment in assessments:
        applied.extend(assessment.rule_ids)

    effective = [facts.responses[a.index] for a in assessments if a.affects_acceptance]
    unresolved = [r for r in effective if r.objection_removed_on is None]
    acknowledged = any(
        a.kind is ResponseKind.ACKNOWLEDGEMENT and a.within_window for a in assessments
    )

    state: AcceptanceState
    basis: AcceptanceBasis | None = None
    acceptance: date | None = None
    if unresolved:
        state = AcceptanceState.OBJECTION_RAISED
        applied.append("R2")
        explanations.append(
            Explanation(
                "acceptance_date",
                ("R2",),
                "A written objection was made within the window and has not been recorded "
                "as removed, so the acceptance date is not fixed yet.",
            )
        )
    elif effective:
        state, basis = AcceptanceState.ACCEPTED, AcceptanceBasis.OBJECTION_REMOVED
        removal_dates = [r.objection_removed_on for r in effective if r.objection_removed_on]
        acceptance = max(removal_dates)
        applied.extend(["R2", "R21"])
        explanations.append(
            Explanation(
                "acceptance_date",
                ("R2", "R21"),
                "Every written objection made within the window has been removed; acceptance "
                f"is the day the last one was removed ({acceptance.isoformat()}).",
            )
        )
    elif window_closed or (params.acknowledgement_ends_window and acknowledged):
        state = AcceptanceState.ACCEPTED
        acceptance = facts.delivery_date
        if acknowledged:
            basis = AcceptanceBasis.ACKNOWLEDGED
            applied.extend(["R1", "R20"])
            text = (
                "The buyer acknowledged the delivery and made no written objection "
                "within the window."
            )
            rule_ids: tuple[str, ...] = ("R1", "R20")
        else:
            basis = AcceptanceBasis.DEEMED
            applied.append("R3")
            text = (
                "No written objection was made within the window, so the delivery date "
                "is the day of deemed acceptance."
            )
            rule_ids = ("R3",)
        explanations.append(Explanation("acceptance_date", rule_ids, text))
    else:
        state = AcceptanceState.WINDOW_OPEN
        applied.append("R20")

    window_day = (today - facts.delivery_date).days if not window_closed else None
    window_remaining = (window_end - today).days if not window_closed else None

    appointed_day = due_date = interest_start = limitation = None
    capped = False
    if acceptance is not None:
        appointed_day = acceptance + timedelta(days=params.appointed_day_period_days + 1)
        applied.append("R4")
        if facts.deal_type is DealType.VERBAL:
            due_date = appointed_day - timedelta(days=1)
            interest_start = appointed_day
            applied.extend(["R5", "R7"])
            explanations.append(
                Explanation(
                    "due_date",
                    ("R5", "R4", "R4a"),
                    "No written agreement: payment is due before the appointed day "
                    f"({appointed_day.isoformat()}).",
                )
            )
        else:
            due_date, capped = _written_due_date(facts, acceptance, rule_set)
            interest_start = due_date + timedelta(days=1)
            applied.extend(["R6", "R7"] + (["R6a"] if capped else []))
            if facts.agreed_payment_days is not None:
                applied.append("A9")
            if capped:
                due_rules: tuple[str, ...] = ("R6", "R6a")
                due_text = (
                    f"Agreed terms exceed {params.max_agreed_payment_days} days from "
                    "acceptance and are capped."
                )
            else:
                due_rules, due_text = ("R6",), "Payment is due on the agreed date."
            explanations.append(Explanation("due_date", due_rules, due_text))
        explanations.append(
            Explanation("interest_start", ("R7",), "Interest runs from this day if unpaid.")
        )
        limitation = add_years_feb28(interest_start, params.limitation_years)
        applied.extend(["R12", "A7", "A11"])
        explanations.append(
            Explanation(
                "indicative_limitation_date",
                ("R12", "A7", "A11"),
                f"Indicative only: about {params.limitation_years} years from the interest "
                "start date. Confirm with counsel.",
            )
        )

    payment_state: PaymentState | None = None
    days_overdue: int | None = None
    if due_date is not None:
        if is_settled:
            payment_state = PaymentState.SETTLED
        elif today > due_date:
            payment_state = PaymentState.OVERDUE
            days_overdue = (today - due_date).days
        else:
            payment_state = PaymentState.NOT_DUE

    rules_applied = tuple(dict.fromkeys(applied))
    return ClockResult(
        as_of=today,
        rule_set_version=rule_set.version,
        acceptance_state=state,
        acceptance_basis=basis,
        window_end=window_end,
        window_day=window_day,
        window_days_remaining=window_remaining,
        acceptance_date=acceptance,
        appointed_day=appointed_day,
        due_date=due_date,
        interest_start=interest_start,
        indicative_limitation_date=limitation,
        payment_state=payment_state,
        days_overdue=days_overdue,
        terms_capped_at_max=capped,
        responses=assessments,
        explanations=tuple(explanations),
        rules_applied=rules_applied,
        unconfirmed_rules=rule_set.unconfirmed(rules_applied),
        pending_reviews=rule_set.pending_reviews,
    )


def _written_due_date(facts: CaseFacts, acceptance: date, rule_set: RuleSet) -> tuple[date, bool]:
    """Agreed due date capped at acceptance + max agreed days (R6, R6a, A9)."""
    params = rule_set.parameters
    cap = acceptance + timedelta(days=params.max_agreed_payment_days)
    if facts.agreed_due_date is not None:
        agreed = facts.agreed_due_date
    else:
        assert facts.agreed_payment_days is not None  # guaranteed by _validate
        agreed = acceptance + timedelta(days=facts.agreed_payment_days)
    if agreed > cap:
        return cap, True
    return agreed, False


def _assess(
    index: int, response: BuyerResponseFact, window_end: date, rule_set: RuleSet
) -> ResponseAssessment:
    params = rule_set.parameters
    within = response.received_on <= window_end
    if response.channel is ResponseChannel.PHONE_NOTE:
        written = params.phone_note_counts_as_written
        channel_rules: tuple[str, ...] = ("R19",)
    elif response.channel is ResponseChannel.OTHER:
        written = params.other_channel_counts_as_written
        channel_rules = ("R19", "A6")
    else:
        written = True
        channel_rules = ("R19",)

    affects = False
    if response.kind is ResponseKind.OBJECTION:
        if not written:
            note, rules = "Not in writing; it does not move the acceptance date.", channel_rules
        elif not within:
            note, rules = (
                "Received after the window; recorded but does not move the acceptance date.",
                ("R3a",) + channel_rules,
            )
        else:
            affects = True
            note, rules = "Written objection within the window.", ("R2",) + channel_rules
    elif response.kind is ResponseKind.ACKNOWLEDGEMENT:
        note = (
            "Acknowledgement within the window; the window still runs."
            if within
            else "Acknowledgement after the window."
        )
        rules = ("R20",)
    else:
        note, rules = "Recorded; no effect on the acceptance date.", ()

    return ResponseAssessment(
        index=index,
        response_id=response.response_id,
        kind=response.kind,
        received_on=response.received_on,
        within_window=within,
        counts_as_written=written,
        affects_acceptance=affects,
        rule_ids=rules,
        note=note,
    )


def _validate(facts: CaseFacts, today: date, rule_set: RuleSet) -> None:
    rule_set.check_applies_to(facts.delivery_date)
    if facts.delivery_date > today:
        raise DomainValidationError("Delivery date cannot be in the future.")

    if facts.deal_type is DealType.VERBAL:
        if facts.agreed_payment_days is not None or facts.agreed_due_date is not None:
            raise DomainValidationError("A verbal deal cannot have agreed payment terms.")
    else:
        has_days = facts.agreed_payment_days is not None
        has_date = facts.agreed_due_date is not None
        if has_days == has_date:
            raise DomainValidationError(
                "A written deal needs exactly one of agreed_payment_days or agreed_due_date."
            )
        days = facts.agreed_payment_days
        if days is not None and (
            isinstance(days, bool)
            or not isinstance(days, int)
            or not 0 <= days <= MAX_AGREED_PAYMENT_DAYS_INPUT
        ):
            raise DomainValidationError(
                f"agreed_payment_days must be an integer from 0 to {MAX_AGREED_PAYMENT_DAYS_INPUT}."
            )
        if facts.agreed_due_date is not None and facts.agreed_due_date < facts.delivery_date:
            raise DomainValidationError("Agreed due date cannot be before the delivery date.")

    _validate_responses(facts.responses, facts.delivery_date, today)


def _validate_responses(
    responses: Sequence[BuyerResponseFact], delivery_date: date, today: date
) -> None:
    for i, response in enumerate(responses):
        where = f"responses[{i}]"
        if not delivery_date <= response.received_on <= today:
            raise DomainValidationError(
                f"{where}.received_on must be between the delivery date and today."
            )
        removed = response.objection_removed_on
        if removed is None:
            continue
        if response.kind is not ResponseKind.OBJECTION:
            raise DomainValidationError(f"{where}: only an objection can be removed.")
        if not response.received_on <= removed <= today:
            raise DomainValidationError(
                f"{where}.objection_removed_on must be between the objection date and today."
            )
