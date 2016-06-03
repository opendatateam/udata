# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from datetime import datetime
from flask_script import prompt, prompt_pass
from flask_security.forms import RegisterForm
from flask_security.utils import encrypt_password
from werkzeug.datastructures import MultiDict

from udata.models import User, datastore

from udata.commands import submanager

log = logging.getLogger(__name__)

m = submanager(
    'user',
    help='User related operations',
    description='Handle all user related operations and maintenance'
)


@m.command
def create():
    '''Create a new user'''
    data = {
        'first_name': prompt('First name'),
        'last_name': prompt('Last name'),
        'email': prompt('Email'),
        'password': prompt_pass('Password'),
        'password_confirm': prompt_pass('Confirm Password'),
    }
    form = RegisterForm(MultiDict(data), csrf_enabled=False)
    if form.validate():
        data['password'] = encrypt_password(data['password'])
        del data['password_confirm']
        data['confirmed_at'] = datetime.utcnow()
        user = datastore.create_user(**data)
        print '\nUser created successfully'
        print 'User(id=%s email=%s)' % (user.id, user.email)
        return
    print '\nError creating user:'
    for errors in form.errors.values():
        print '\n'.join(errors)


@m.command
def activate():
    '''Activate an existing user (validate their email confirmation)'''
    email = prompt('Email')
    user = User.objects(email=email).first()
    if not user:
        print 'Invalid user'
        return
    if user.confirmed_at is not None:
        print 'User email address already confirmed'
        return
    user.confirmed_at = datetime.utcnow()
    user.save()
    print 'User activated successfully'


@m.command
def delete():
    '''Delete an existing user'''
    email = prompt('Email')
    user = User.objects(email=email).first()
    if not user:
        print 'Invalid user'
        return
    user.delete()
    print 'User deleted successfully'


@m.command
def set_admin(email):
    '''Set an user as administrator'''
    user = datastore.get_user(email)
    print 'Adding admin role to user %s (%s)' % (user.fullname, user.email)
    role = datastore.find_or_create_role('admin')
    datastore.add_role_to_user(user, role)
    print 'User %s (%s) is now administrator' % (user.fullname, user.email)


@m.command
def password(email):
    user = datastore.get_user(email)
    user.password = encrypt_password(prompt_pass('Enter new password'))
    user.save()
