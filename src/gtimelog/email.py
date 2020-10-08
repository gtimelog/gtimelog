import collections
import email
import logging
import smtplib
from contextlib import closing
from email.mime import text
from email.utils import formataddr, parseaddr
from gettext import gettext as _

from gtimelog import DEBUG, __version__


MailProtocol = collections.namedtuple('MailProtocol', 'factory, startssl')
MAIL_PROTOCOLS = {
    'SMTP': MailProtocol(smtplib.SMTP, False),
    'SMTPS': MailProtocol(smtplib.SMTP_SSL, False),
    'SMTP (StartTLS)': MailProtocol(smtplib.SMTP, True),
}

log = logging.getLogger('email')


class EmailError(Exception):
    pass


def isascii(s):
    return all(0 <= ord(c) <= 127 for c in s)


def address_header(name_and_address):
    if isascii(name_and_address):
        return name_and_address
    name, addr = parseaddr(name_and_address)
    name = str(email.header.Header(name, 'UTF-8'))
    return formataddr((name, addr))


def subject_header(header):
    if isascii(header):
        return header
    return email.header.Header(header, 'UTF-8')


def prepare_message(sender, recipient, subject, body):
    if isascii(body):
        msg = text.MIMEText(body)
    else:
        msg = text.MIMEText(body, _charset="UTF-8")
    if sender:
        msg["From"] = address_header(sender)
    msg["To"] = address_header(recipient)
    msg["Subject"] = subject_header(subject)
    msg["User-Agent"] = "gtimelog/{}".format(__version__)
    return msg


def send_email(protocol, server, port, username, sender, recipient, subject, body, password):

    sender_name, sender_address = parseaddr(sender)
    recipient_name, recipient_address = parseaddr(recipient)
    msg = prepare_message(sender, recipient, subject, body)

    factory, starttls = MAIL_PROTOCOLS[protocol]
    try:
        log.debug('Connecting to %s port %s',
                  server, port or '(default)')
        with closing(factory(server, port)) as smtp:
            if DEBUG:
                smtp.set_debuglevel(1)
            if starttls:
                log.debug('Issuing STARTTLS')
                smtp.starttls()
            if username:
                log.debug('Logging in as %s', username)
                smtp.login(username, password)
            log.debug('Sending email from %s to %s',
                      sender_address, recipient_address)
            smtp.sendmail(sender_address, [recipient_address], msg.as_string())
            log.debug('Closing SMTP connection')
    except (OSError, smtplib.SMTPException) as e:
        log.error(_("Couldn't send mail: %s"), e)
        raise EmailError(e)
    else:
        log.debug('Email sent!')
