import logging
from datetime import UTC, datetime

import click
from flask import current_app
from flask_security.forms import RegisterForm
from flask_security.utils import hash_password
from werkzeug.datastructures import MultiDict

from udata.commands import cli, exit_with_error, success
from udata.models import User, datastore

log = logging.getLogger(__name__)


@cli.group("user")
def grp():
    """User related operations"""
    pass


@grp.command()
@click.option("--first-name")
@click.option("--last-name")
@click.option("--email")
@click.option("--password")
@click.option("--admin", is_flag=True)
def create(first_name, last_name, email, password, admin):
    """Create a new user"""
    data = {
        "first_name": first_name or click.prompt("First name"),
        "last_name": last_name or click.prompt("Last name"),
        "email": email or click.prompt("Email"),
        "password": password or click.prompt("Password", hide_input=True),
        "password_confirm": password or click.prompt("Confirm Password", hide_input=True),
    }
    # Until https://github.com/mattupstate/flask-security/issues/672 is fixed
    with current_app.test_request_context():
        form = RegisterForm(MultiDict(data), meta={"csrf": False})
    if form.validate():
        data["password"] = hash_password(data["password"])
        del data["password_confirm"]
        data["confirmed_at"] = datetime.now(UTC)
        user = datastore.create_user(**data)
        if admin:
            role = datastore.find_or_create_role("admin")
            datastore.add_role_to_user(user, role)
        success("User(id={u.id} email={u.email}) created".format(u=user))
        return user
    errors = "\n".join("\n".join([str(m) for m in e]) for e in form.errors.values())
    exit_with_error("Error creating user", errors)


@grp.command()
def activate():
    """Activate an existing user (validate their email confirmation)"""
    email = click.prompt("Email")
    user = User.objects(email=email).first()
    if not user:
        exit_with_error("Invalid user")
    if user.confirmed_at is not None:
        exit_with_error("User email address already confirmed")
        return
    user.confirmed_at = datetime.now(UTC)
    user.save()
    success("User activated successfully")


@grp.command()
def delete():
    """Delete an existing user"""
    email = click.prompt("Email")
    user: User = User.objects(email=email).first()
    if not user:
        exit_with_error("Invalid user")
    user.mark_as_deleted()
    success("User marked as deleted successfully")


@grp.command()
@click.argument("email")
def set_admin(email):
    """Set an user as administrator"""
    user: User = datastore.find_user(email=email)
    log.info("Adding admin role to user %s (%s)", user.fullname, user.email)
    role = datastore.find_or_create_role("admin")
    datastore.add_role_to_user(user, role)
    success(f"User {user.fullname} {user.email}] is now administrator")


@grp.command()
@click.argument("email")
def password(email):
    user: User = datastore.find_user(email=email)
    password = click.prompt("Enter new password", hide_input=True)
    user.password = hash_password(password)
    user.save()
    success(msg=f"New password set for user {email}")


@grp.command()
@click.argument("email")
def rotate_password(email):
    """
    Ask user for password rotation on next login and reset any current session
    """
    user: User = datastore.find_user(email=email)
    user.password_rotation_demanded = datetime.now(UTC)
    user.save()
    # Reset ongoing sessions by uniquifier
    datastore.set_uniquifier(user)
    success(f"Password rotated for user {email}")


@grp.command()
@click.argument("email")
def unset_two_factor(email):
    user: User = datastore.find_user(email=email)
    user.tf_primary_method = None
    user.tf_totp_secret = None
    user.save()
    success(f"2FA has been unset for user {email}")
