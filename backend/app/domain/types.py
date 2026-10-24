"""Shared domain enumerations. Values match DATABASE.md so they can be stored unchanged."""

from enum import StrEnum


class DealType(StrEnum):
    VERBAL = "verbal"
    WRITTEN = "written"


class ResponseKind(StrEnum):
    OBJECTION = "objection"
    ACKNOWLEDGEMENT = "acknowledgement"
    OTHER = "other"


class ResponseChannel(StrEnum):
    EMAIL = "email"
    LETTER = "letter"
    WHATSAPP = "whatsapp"
    IN_PERSON_WRITTEN = "in_person_written"
    PHONE_NOTE = "phone_note"
    OTHER = "other"


class EnterpriseClass(StrEnum):
    MICRO = "micro"
    SMALL = "small"
    MEDIUM = "medium"


class MajorActivity(StrEnum):
    MANUFACTURING = "manufacturing"
    SERVICES = "services"
    TRADING = "trading"


class UdyamVerificationStatus(StrEnum):
    SELF_DECLARED = "self_declared"
    CERTIFICATE_UPLOADED = "certificate_uploaded"
    PROVIDER_VERIFIED_SANDBOX = "provider_verified_sandbox"
    PROVIDER_VERIFIED_LIVE = "provider_verified_live"


class EvidenceKind(StrEnum):
    INVOICE = "invoice"
    DELIVERY_CHALLAN = "delivery_challan"
    DELIVERY_PHOTO = "delivery_photo"
    PURCHASE_ORDER = "purchase_order"
    WRITTEN_TERMS = "written_terms"
    EMAIL = "email"
    CHAT_EXPORT = "chat_export"
    TRACKING_RECORD = "tracking_record"
    UDYAM_CERTIFICATE = "udyam_certificate"
    BUYER_RESPONSE = "buyer_response"
    PAYMENT_PROOF = "payment_proof"
    COMMUNICATION_PROOF = "communication_proof"
    OTHER = "other"
