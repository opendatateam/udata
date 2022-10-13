import email_validator
from flask import current_app
from udata.tasks import task


@task
def sendmail(msg):
    mail = current_app.extensions.get("mail")
    mail.send(msg)


class UdataMailUtil:

    def __init__(self, app):
        pass

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

    def normalize(self, email):
        validator_args = current_app.config.get('EMAIL_VALIDATOR_ARGS') or {}
        valid = email_validator.validate_email(email, **validator_args)
        return valid.email

    def validate(self, email):
        validator_args = current_app.config.get('EMAIL_VALIDATOR_ARGS') or {}
        valid = email_validator.validate_email(email, **validator_args)
        return valid.email
