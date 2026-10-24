"""Supplier-scoped queries for the demo vertical slice (ARCHITECTURE.md Section 3.1).

A row belonging to another supplier is indistinguishable from a missing row (returns None),
so callers answer 404 without revealing existence (ARCHITECTURE.md Section 8.4).
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    BankRate,
    Buyer,
    BuyerResponse,
    Case,
    EvidenceItem,
    Supplier,
    TimelineEventRow,
)


def demo_supplier(session: Session) -> Supplier | None:
    return session.scalars(
        select(Supplier).where(Supplier.is_demo.is_(True)).order_by(Supplier.created_at)
    ).first()


def list_buyers(session: Session, supplier_id: str) -> list[Buyer]:
    return list(
        session.scalars(
            select(Buyer).where(Buyer.supplier_id == supplier_id).order_by(Buyer.legal_name)
        )
    )


def get_buyer(session: Session, supplier_id: str, buyer_id: str) -> Buyer | None:
    return session.scalars(
        select(Buyer).where(Buyer.supplier_id == supplier_id, Buyer.id == buyer_id)
    ).first()


def list_cases(session: Session, supplier_id: str, limit: int) -> list[Case]:
    return list(
        session.scalars(
            select(Case)
            .where(Case.supplier_id == supplier_id)
            .order_by(Case.delivery_date.desc(), Case.created_at.desc())
            .limit(limit)
        )
    )


def get_case(session: Session, supplier_id: str, case_id: str) -> Case | None:
    return session.scalars(
        select(Case).where(Case.supplier_id == supplier_id, Case.id == case_id)
    ).first()


def count_cases_with_prefix(session: Session, supplier_id: str, prefix: str) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(Case)
            .where(Case.supplier_id == supplier_id, Case.reference.startswith(prefix))
        )
        or 0
    )


def list_responses(session: Session, case_id: str) -> list[BuyerResponse]:
    return list(
        session.scalars(
            select(BuyerResponse)
            .where(BuyerResponse.case_id == case_id)
            .order_by(BuyerResponse.received_on, BuyerResponse.created_at)
        )
    )


def get_response(session: Session, case_id: str, response_id: str) -> BuyerResponse | None:
    return session.scalars(
        select(BuyerResponse).where(
            BuyerResponse.case_id == case_id, BuyerResponse.id == response_id
        )
    ).first()


def list_evidence(session: Session, case_id: str) -> list[EvidenceItem]:
    return list(
        session.scalars(
            select(EvidenceItem)
            .where(EvidenceItem.case_id == case_id)
            .order_by(EvidenceItem.received_at)
        )
    )


def get_evidence(session: Session, supplier_id: str, evidence_id: str) -> EvidenceItem | None:
    return session.scalars(
        select(EvidenceItem).where(
            EvidenceItem.supplier_id == supplier_id, EvidenceItem.id == evidence_id
        )
    ).first()


def case_storage_bytes(session: Session, case_id: str) -> int:
    return (
        session.scalar(
            select(func.coalesce(func.sum(EvidenceItem.size_bytes), 0)).where(
                EvidenceItem.case_id == case_id
            )
        )
        or 0
    )


def list_timeline(session: Session, case_id: str) -> list[TimelineEventRow]:
    return list(
        session.scalars(
            select(TimelineEventRow)
            .where(TimelineEventRow.case_id == case_id)
            .order_by(TimelineEventRow.seq)
        )
    )


def list_bank_rates(session: Session) -> list[BankRate]:
    return list(session.scalars(select(BankRate).order_by(BankRate.effective_from)))
