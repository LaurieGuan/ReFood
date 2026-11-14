"""Local-only notification delivery. No actual mail is sent by this module."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.marketplace import lock_marketplace
from database.orm_models import TradeNotificationRow
from schemas.marketplace import ExchangeProposal
from services.trade_email import build_trade_confirmation

# Reserved example.org addresses; never substitute real addresses in this demo.
DEMO_ADDRESSES = {'alice': 'alice@example.org', 'bob': 'bob@example.org',
                  'demo_user': 'demo@example.org'}


def process_demo_notifications(engine, deliver):
    """Deliver pending/failed intents to a local callback, returning counts.

    The callback is for local previews only and must not send email. The global
    marketplace lock serializes processors; errors remain retryable. This is not
    a delivery guarantee for SMTP, which needs its own provider/idempotency design.
    """
    sent = failed = 0
    with Session(engine) as session, session.begin():
        lock_marketplace(session)
        rows = session.scalars(select(TradeNotificationRow).where(
            TradeNotificationRow.status.in_(['pending', 'failed']))
            .order_by(TradeNotificationRow.proposal_id, TradeNotificationRow.recipient_id)).all()
        for row in rows:
            row.attempts += 1
            try:
                proposal = ExchangeProposal.model_validate(row.payload)
                partner = (proposal.proposer_id if row.recipient_id == proposal.target_owner_id
                           else proposal.target_owner_id)
                message = build_trade_confirmation(proposal, row.recipient_id,
                    DEMO_ADDRESSES[row.recipient_id], DEMO_ADDRESSES[partner], 'refood@example.org')
                deliver(message)
            except Exception:
                row.status = 'failed'
                failed += 1
            else:
                row.status = 'previewed'
                sent += 1
    return {'previewed': sent, 'failed': failed}
