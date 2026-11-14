"""Prepare a trade email without sending it or looking up user identities."""
from email.message import EmailMessage
from email.utils import parseaddr
from schemas.marketplace import ExchangeProposal, ProposalStatus


def _address(value: str) -> str:
    name, address = parseaddr(value)
    if name or address != value or address.count('@') != 1:
        raise ValueError('A single email address is required')
    local, domain = address.split('@')
    if not local or not domain or any(c.isspace() for c in address):
        raise ValueError('A single email address is required')
    return address


def build_trade_confirmation(proposal: ExchangeProposal, recipient_id: str,
                             recipient_email: str, partner_email: str,
                             sender_email: str) -> EmailMessage:
    """Build one message after acceptance; caller must supply verified addresses."""
    proposal = ExchangeProposal.model_validate(proposal.model_dump(mode='json'))
    if proposal.status != ProposalStatus.ACCEPTED:
        raise ValueError('Trade must be accepted')
    if recipient_id not in (proposal.target_owner_id, proposal.proposer_id):
        raise ValueError('Recipient must be a participant')
    recipient_email = _address(recipient_email)
    partner_email = _address(partner_email)
    sender_email = _address(sender_email)
    message = EmailMessage()
    message['From'] = sender_email
    message['To'] = recipient_email
    message['Reply-To'] = partner_email
    message['Subject'] = 'REFOOD — votre proposition de troc a été acceptée'
    message.set_content(
        'Bonjour,\n\nVotre proposition de troc a été acceptée.\n'
        f"Échange : {proposal.proposer_item.name} contre {proposal.target_item.name}.\n\n"
        f'Vous pouvez contacter l’autre participant à {partner_email} pour convenir du lieu et du moment de rencontre.\n\n'
        'L’équipe REFOOD\n'
    )
    return message
