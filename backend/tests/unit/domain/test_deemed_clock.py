"""DeemedClock unit tests beyond the legal fixtures: validation, metadata and boundaries."""

from dataclasses import replace
from datetime import date, timedelta

import pytest

from app.domain.deemed_clock import (
    AcceptanceBasis,
    AcceptanceState,
    BuyerResponseFact,
    CaseFacts,
    PaymentState,
    compute_clock,
)
from app.domain.errors import DomainValidationError
from app.domain.rules import RuleSet
from app.domain.types import DealType, ResponseChannel, ResponseKind

DELIVERY = date(2026, 11, 1)
VERBAL = CaseFacts(delivery_date=DELIVERY, deal_type=DealType.VERBAL)


def _response(
    kind: ResponseKind = ResponseKind.OBJECTION,
    day: int = 3,
    channel: ResponseChannel = ResponseChannel.EMAIL,
    removed_day: int | None = None,
) -> BuyerResponseFact:
    return BuyerResponseFact(
        kind=kind,
        received_on=DELIVERY + timedelta(days=day),
        channel=channel,
        objection_removed_on=(
            DELIVERY + timedelta(days=removed_day) if removed_day is not None else None
        ),
    )


def test_window_counts_down_from_day_0(rule_set: RuleSet) -> None:
    result = compute_clock(VERBAL, DELIVERY, rule_set)
    assert result.acceptance_state is AcceptanceState.WINDOW_OPEN
    assert result.window_day == 0
    assert result.window_days_remaining == 15
    assert result.window_end == date(2026, 11, 16)
    assert result.due_date is None and result.payment_state is None


def test_every_result_lists_unconfirmed_rules_and_pending_reviews(rule_set: RuleSet) -> None:
    result = compute_clock(VERBAL, date(2026, 11, 20), rule_set)
    assert result.rule_set_version == "msmed-v1"
    assert {"R3", "R4a", "R5", "R7"} <= set(result.rules_applied)
    assert set(result.unconfirmed_rules) == set(result.rules_applied)  # nothing confirmed yet
    assert "LR-21" in result.pending_reviews
    assert any(e.field == "acceptance_date" and "R3" in e.rule_ids for e in result.explanations)


def test_objection_removed_inside_window_fixes_acceptance_early(rule_set: RuleSet) -> None:
    facts = replace(VERBAL, responses=(_response(day=2, removed_day=5),))
    result = compute_clock(facts, DELIVERY + timedelta(days=6), rule_set)
    assert result.acceptance_state is AcceptanceState.ACCEPTED
    assert result.acceptance_basis is AcceptanceBasis.OBJECTION_REMOVED
    assert result.acceptance_date == DELIVERY + timedelta(days=5)


def test_one_of_two_objections_still_open_keeps_state_raised(rule_set: RuleSet) -> None:
    facts = replace(VERBAL, responses=(_response(day=2, removed_day=4), _response(day=6)))
    result = compute_clock(facts, date(2026, 12, 1), rule_set)
    assert result.acceptance_state is AcceptanceState.OBJECTION_RAISED
    assert result.acceptance_date is None


def test_response_assessments_explain_their_effect(rule_set: RuleSet) -> None:
    facts = replace(
        VERBAL,
        responses=(
            _response(day=16),  # late
            _response(channel=ResponseChannel.PHONE_NOTE),  # not written
            _response(kind=ResponseKind.OTHER),
            _response(kind=ResponseKind.ACKNOWLEDGEMENT, day=20),
        ),
    )
    result = compute_clock(facts, date(2026, 12, 1), rule_set)
    late, phone, other, ack = result.responses
    assert not late.within_window and not late.affects_acceptance and "R3a" in late.rule_ids
    assert not phone.counts_as_written and not phone.affects_acceptance
    assert other.rule_ids == () and not other.affects_acceptance
    assert not ack.within_window
    assert result.acceptance_basis is AcceptanceBasis.DEEMED  # acknowledgement was after Day 15


def test_settled_case_reports_settled(rule_set: RuleSet) -> None:
    result = compute_clock(VERBAL, date(2026, 12, 1), rule_set, is_settled=True)
    assert result.payment_state is PaymentState.SETTLED and result.days_overdue is None


def test_written_deal_due_date_not_yet_reached(rule_set: RuleSet) -> None:
    facts = CaseFacts(DELIVERY, DealType.WRITTEN, agreed_payment_days=30)
    result = compute_clock(facts, date(2026, 11, 20), rule_set)
    assert result.payment_state is PaymentState.NOT_DUE
    assert result.due_date == date(2026, 12, 1)


def test_agreed_days_zero_means_due_on_acceptance(rule_set: RuleSet) -> None:
    facts = CaseFacts(DELIVERY, DealType.WRITTEN, agreed_payment_days=0)
    result = compute_clock(facts, date(2026, 11, 20), rule_set)
    assert result.due_date == DELIVERY and result.interest_start == DELIVERY + timedelta(days=1)


def test_acknowledgement_can_end_window_when_configured(rule_set: RuleSet) -> None:
    alt = replace(
        rule_set, parameters=replace(rule_set.parameters, acknowledgement_ends_window=True)
    )
    facts = replace(VERBAL, responses=(_response(kind=ResponseKind.ACKNOWLEDGEMENT, day=2),))
    result = compute_clock(facts, DELIVERY + timedelta(days=3), alt)
    assert result.acceptance_basis is AcceptanceBasis.ACKNOWLEDGED
    assert result.acceptance_date == DELIVERY


def test_phone_objection_counts_when_configured(rule_set: RuleSet) -> None:
    alt = replace(
        rule_set, parameters=replace(rule_set.parameters, phone_note_counts_as_written=True)
    )
    facts = replace(VERBAL, responses=(_response(channel=ResponseChannel.PHONE_NOTE),))
    assert (
        compute_clock(facts, date(2026, 12, 1), alt).acceptance_state
        is AcceptanceState.OBJECTION_RAISED
    )


@pytest.mark.parametrize(
    ("facts", "today", "message"),
    [
        (VERBAL, DELIVERY - timedelta(days=1), "future"),
        (replace(VERBAL, delivery_date=date(2006, 1, 1)), date(2026, 1, 1), "applies from"),
        (replace(VERBAL, agreed_payment_days=30), DELIVERY, "verbal deal"),
        (replace(VERBAL, agreed_due_date=DELIVERY), DELIVERY, "verbal deal"),
        (CaseFacts(DELIVERY, DealType.WRITTEN), DELIVERY, "exactly one"),
        (
            CaseFacts(DELIVERY, DealType.WRITTEN, agreed_payment_days=30, agreed_due_date=DELIVERY),
            DELIVERY,
            "exactly one",
        ),
        (CaseFacts(DELIVERY, DealType.WRITTEN, agreed_payment_days=-1), DELIVERY, "0 to 365"),
        (CaseFacts(DELIVERY, DealType.WRITTEN, agreed_payment_days=366), DELIVERY, "0 to 365"),
        (CaseFacts(DELIVERY, DealType.WRITTEN, agreed_payment_days=True), DELIVERY, "0 to 365"),
        (
            CaseFacts(DELIVERY, DealType.WRITTEN, agreed_due_date=DELIVERY - timedelta(days=1)),
            DELIVERY,
            "before the delivery",
        ),
        (replace(VERBAL, responses=(_response(day=-1),)), DELIVERY, "between the delivery"),
        (replace(VERBAL, responses=(_response(day=5),)), DELIVERY + timedelta(days=4), "between"),
        (
            replace(VERBAL, responses=(_response(ResponseKind.ACKNOWLEDGEMENT, removed_day=4),)),
            DELIVERY + timedelta(days=5),
            "only an objection",
        ),
        (
            replace(VERBAL, responses=(_response(day=4, removed_day=3),)),
            DELIVERY + timedelta(days=5),
            "objection date and today",
        ),
        (
            replace(VERBAL, responses=(_response(day=4, removed_day=9),)),
            DELIVERY + timedelta(days=5),
            "objection date and today",
        ),
    ],
)
def test_invalid_facts_are_rejected(
    facts: CaseFacts, today: date, message: str, rule_set: RuleSet
) -> None:
    with pytest.raises(DomainValidationError, match=message):
        compute_clock(facts, today, rule_set)


def test_engine_reads_periods_from_the_rule_set(rule_set: RuleSet) -> None:
    alt = replace(rule_set, parameters=replace(rule_set.parameters, objection_window_days=10))
    assert compute_clock(VERBAL, DELIVERY, alt).window_end == DELIVERY + timedelta(days=10)
