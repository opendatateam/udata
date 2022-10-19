from flask import current_app
from flask_security import MailUtil
from udata.tasks import task


@task
def sendmail(msg):
    mail = current_app.extensions.get("mail")
    mail.send(msg)


class UdataMailUtil(MailUtil):

    def __init__(self, app):
        super().__init__(app)

    def send_mail(self, template, subject, recipient, sender, body, html, user, **kwargs):
        from flask_mail import Message

        # In Flask-Mail, sender can be a two element tuple -- (name, address)
        if isinstance(sender, tuple) and len(sender) == 2:
            sender = (str(sender[0]), str(sender[1]))
        else:
            sender = str(sender)
        msg = Message(subject, sender=sender, recipients=[recipient])
        msg.body = body
        msg.html = html

        sendmail.delay(msg)
