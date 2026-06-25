from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import re

app = FastAPI(title="QueueStorm Ticket Classifier")


class TicketRequest(BaseModel):
    ticket_id: str
    channel: Optional[str] = None
    locale: Optional[str] = None
    message: str


class TicketResponse(BaseModel):
    ticket_id: str
    case_type: str
    severity: str
    department: str
    agent_summary: str
    human_review_required: bool
    confidence: float


PHISHING_KEYWORDS = [
    "otp", "pin", "password", "asked for", "asking for", "share your",
    "give me your", "verify your", "confirm your pin", "confirm your otp",
    "someone called", "received a call", "got a call", "bkash agent",
    "scam", "fraud call", "suspicious call", "suspicious sms",
    "send your", "send me your", "told me to share", "asked me to share",
    "asked my otp", "asked my pin", "asking my otp", "asking my pin",
]

WRONG_TRANSFER_KEYWORDS = [
    "wrong number", "wrong account", "wrong person", "wrong recipient",
    "sent to wrong", "transferred to wrong", "mistakenly sent",
    "accidentally sent", "wrong bkash", "sent by mistake",
    "wrong transfer", "wrong mobile",
]

PAYMENT_FAILED_KEYWORDS = [
    "payment failed", "transaction failed", "failed transaction",
    "balance deducted", "money deducted", "amount deducted",
    "deducted but", "charged but", "not received", "not credited",
    "failed but", "unsuccessful", "payment not", "did not go through",
    "payment declined", "declined",
]

REFUND_KEYWORDS = [
    "refund", "money back", "get my money back", "return my money",
    "i want back", "give me back", "cancel", "cancelled", "reversal",
    "i changed my mind", "reverse the transaction",
]


def classify(message: str):
    text = message.lower()

    # Check phishing first (highest priority)
    phishing_score = sum(1 for kw in PHISHING_KEYWORDS if kw in text)
    wrong_transfer_score = sum(1 for kw in WRONG_TRANSFER_KEYWORDS if kw in text)
    payment_failed_score = sum(1 for kw in PAYMENT_FAILED_KEYWORDS if kw in text)
    refund_score = sum(1 for kw in REFUND_KEYWORDS if kw in text)

    scores = {
        "phishing_or_social_engineering": phishing_score,
        "wrong_transfer": wrong_transfer_score,
        "payment_failed": payment_failed_score,
        "refund_request": refund_score,
    }

    best = max(scores, key=scores.get)
    best_score = scores[best]

    if best_score == 0:
        case_type = "other"
        confidence = 0.6
    else:
        case_type = best
        total = sum(scores.values())
        confidence = round(min(0.95, 0.6 + (best_score / max(total, 1)) * 0.4), 2)

    return case_type, confidence


def get_severity(case_type: str, message: str) -> str:
    text = message.lower()

    if case_type == "phishing_or_social_engineering":
        return "critical"

    if case_type == "wrong_transfer":
        # Large amounts = higher severity
        amounts = re.findall(r'\d+', text)
        if amounts and max(int(a) for a in amounts) >= 1000:
            return "high"
        return "high"

    if case_type == "payment_failed":
        return "high"

    if case_type == "refund_request":
        # Check urgency words
        if any(w in text for w in ["urgent", "immediately", "asap", "emergency"]):
            return "medium"
        return "low"

    return "low"


def get_department(case_type: str, severity: str) -> str:
    if case_type == "phishing_or_social_engineering":
        return "fraud_risk"
    if case_type == "wrong_transfer":
        return "dispute_resolution"
    if case_type == "payment_failed":
        return "payments_ops"
    if case_type == "refund_request":
        if severity in ("high", "critical"):
            return "dispute_resolution"
        return "customer_support"
    return "customer_support"


def build_summary(case_type: str, message: str) -> str:
    msg = message.strip().rstrip(".")

    if case_type == "wrong_transfer":
        amounts = re.findall(r'\d[\d,]*', message)
        amount_str = f" of {amounts[0]} BDT" if amounts else ""
        return f"Customer reports a wrong transfer{amount_str} and requests recovery assistance."

    if case_type == "payment_failed":
        return "Customer reports a failed transaction where the balance may have been deducted without successful payment."

    if case_type == "phishing_or_social_engineering":
        return "Customer reports a suspicious contact attempting to obtain sensitive account information."

    if case_type == "refund_request":
        return "Customer is requesting a refund for a recent transaction."

    return f"Customer reported an issue: {msg[:120]}."


@app.get("/health")
def health():
    return {"status": "ok", "service": "ticket-classifier"}


@app.post("/sort-ticket", response_model=TicketResponse)
def sort_ticket(ticket: TicketRequest):
    case_type, confidence = classify(ticket.message)
    severity = get_severity(case_type, ticket.message)
    department = get_department(case_type, severity)
    summary = build_summary(case_type, ticket.message)
    human_review = severity == "critical" or case_type == "phishing_or_social_engineering"

    return TicketResponse(
        ticket_id=ticket.ticket_id,
        case_type=case_type,
        severity=severity,
        department=department,
        agent_summary=summary,
        human_review_required=human_review,
        confidence=confidence,
    )
