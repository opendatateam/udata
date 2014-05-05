# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask.ext.script import Command, prompt, prompt_pass
from flask.ext.security.forms import RegisterForm
from flask.ext.security.utils import encrypt_password
from werkzeug.datastructures import MultiDict

from udata.models import User, datastore

from udata.commands import manager


class CreateUserCommand(Command):
    '''Create a new user'''
    def run(self):
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
            user = datastore.create_user(**data)
            print '\nUser created successfully'
            print 'User(id=%s email=%s)' % (user.id, user.email)
            return
        print '\nError creating user:'
        for errors in form.errors.values():
            print '\n'.join(errors)


class DeleteUserCommand(Command):
    '''Delete an existing user'''
    def run(self):
        email = prompt('Email')
        user = User.objects(email=email).first()
        if not user:
            print 'Invalid user'
            return
        user.delete()
        print 'User deleted successfully'


manager.add_command('create_user', CreateUserCommand())
manager.add_command('delete_user', DeleteUserCommand())
