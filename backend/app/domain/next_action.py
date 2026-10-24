"""The single next step shown on a case (T2.6; DESIGN.md Section 9.4).

Rules are checked in priority order and the first match wins. The domain returns a code plus
context; user-facing wording lives in the frontend copy catalogue.
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from app.domain.checklist import ChecklistResult, IntegrityStatus, ItemStatus
from app.domain.deemed_clock import AcceptanceState, ClockResult, PaymentState

# Checklist items that a supplier fixes by adding evidence or details (DESIGN.md 9.4 rule 4).
EVIDENCE_ITEMS = ("C06", "C07", "C08", "C10")


class NextActionCode(StrEnum):
    REVIEW_INTEGRITY = "review_integrity"
    RESOLVE_OBJECTION = "resolve_objection"
    SEND_INTIMATION = "send_intimation"
    COMPLETE_EVIDENCE = "complete_evidence"
    SEND_DEMAND = "send_demand"
    GENERATE_PACK = "generate_pack"
    SHARE_OR_FILE = "share_or_file"
    WAIT = "wait"
    CLOSE_CASE = "close_case"


@dataclass(frozen=True)
class NextAction:
    code: NextActionCode
    checklist_item: str | None = None
    until: date | None = None  # for WAIT: the next date something changes


def decide_next_action(
    clock: ClockResult,
    checklist: ChecklistResult,
    *,
    integrity: IntegrityStatus,
    intimation_done: bool,
    demand_done: bool,
    pack_exists: bool,
) -> NextAction:
    if integrity is IntegrityStatus.FAILED:
        return NextAction(NextActionCode.REVIEW_INTEGRITY)
    if clock.acceptance_state is AcceptanceState.OBJECTION_RAISED:
        return NextAction(NextActionCode.RESOLVE_OBJECTION)
    if not intimation_done and clock.acceptance_state is AcceptanceState.WINDOW_OPEN:
        return NextAction(NextActionCode.SEND_INTIMATION)
    for item_id in EVIDENCE_ITEMS:
        if checklist.item(item_id).status is ItemStatus.MISSING:
            return NextAction(NextActionCode.COMPLETE_EVIDENCE, checklist_item=item_id)
    if clock.payment_state is PaymentState.OVERDUE:
        if not demand_done:
            return NextAction(NextActionCode.SEND_DEMAND)
        if not pack_exists:
            return NextAction(NextActionCode.GENERATE_PACK)
        return NextAction(NextActionCode.SHARE_OR_FILE)
    if clock.payment_state is PaymentState.SETTLED:
        return NextAction(NextActionCode.CLOSE_CASE)
    if clock.payment_state is PaymentState.NOT_DUE:
        return NextAction(NextActionCode.WAIT, until=clock.due_date)
    return NextAction(NextActionCode.WAIT, until=clock.window_end)
