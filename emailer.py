"""Gmail SMTP with explicit UI confirmation handled by the caller."""
import re
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate
from config import secret


class EmailError(RuntimeError):
    pass


def addresses(value, optional=False):
    if not value.strip() and optional:
        return []
    result = [email.strip() for email in value.split(',')]
    if any(not re.fullmatch(r'[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+', email) for email in result):
        raise EmailError('Enter valid email addresses, separated by commas.')
    return result


def _connection():
    address = secret('GMAIL_ADDRESS')
    password = secret('GMAIL_APP_PASSWORD').replace(' ', '')
    if not address or not password:
        raise EmailError('Add GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env or Cloud Secrets.')
    server = None
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=20)
        server.ehlo()
        server.starttls(context=ssl.create_default_context())
        server.ehlo()
        server.login(address, password)
        return server
    except Exception:
        if server is not None:
            server.close()
        raise


def friendly_error(exc):
    if isinstance(exc, EmailError):
        return str(exc)
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return 'Gmail rejected the login. Check the Gmail address and 16-character App Password; 2-Step Verification must be enabled.'
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return 'Gmail rejected the recipient. Check the destination address.'
    if isinstance(exc, (OSError, TimeoutError, smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected)):
        return 'Gmail connection failed. Check your network; outbound SMTP port 587 may be blocked by your host.'
    return 'Gmail could not complete the request. Check account permissions and try again.'


def test_connection():
    try:
        with _connection() as server:
            server.noop()
    except Exception as exc:
        raise EmailError(friendly_error(exc)) from None


def send(to, cc, subject, body, attachments=()):
    recipients = addresses(to) + addresses(cc, optional=True)
    if not subject.strip() or '\n' in subject or '\r' in subject:
        raise EmailError('Enter a subject on a single line.')
    msg = EmailMessage()
    msg['From'] = secret('GMAIL_ADDRESS')
    msg['To'] = ', '.join(addresses(to))
    if cc.strip():
        msg['Cc'] = ', '.join(addresses(cc, optional=True))
    msg['Subject'] = subject
    msg['Date'] = formatdate(localtime=True)
    msg.set_content(body)
    for filename, content, subtype in attachments:
        msg.add_attachment(content, maintype='application', subtype=subtype, filename=filename)
    try:
        with _connection() as server:
            refused = server.send_message(msg, to_addrs=recipients)
            return {'status': 'partial' if refused else 'sent',
                    'error': 'Some recipients were rejected; other recipients accepted.' if refused else None}
    except Exception as exc:
        raise EmailError(friendly_error(exc)) from None
