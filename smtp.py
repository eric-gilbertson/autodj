import smtplib
import socket
from email.mime.text import MIMEText
from smtp_credentials import smtp_auth

def send_email(recipient, subject, body=""):
    '''uses smtp with gmail server to deliver a message'''

    body = '{}\n\nSent from: {}'.format(body, socket.gethostname())

    mail_host = smtp_auth.get('host', None)
    if not mail_host:
        return

    # credentials
    username = smtp_auth['username']
    password = smtp_auth['password']

    fromaddr = 'webapp@kzsu.stanford.edu'

    # constructing the MIME
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = fromaddr
    msg['To'] = recipient

    server = smtplib.SMTP(mail_host)
    #server.set_debuglevel(2)
    server.starttls()
    if len(username) > 0:
        server.login(username, password)

    server.sendmail(fromaddr, recipient, msg.as_string())
    server.quit()

if __name__ == "__main__":
    send_email("ericg@kzsu.stanford.edu", "test_subject", "test_body")

