# Features

## Passwords rotation

To ask a user to rotate its password, udata provides in the user model the field `password_rotation_demanded`. This field is a DateTimeField set to `None` by default. If set to a date, the next login attempt of the user will result in an error, asking it to change its password.  
When doing so by the password recovery mechanism, the field `password_rotation_demanded` will be set to `None` and the field `password_rotation_performed` will be set to the date of the paasword change, for tracking purposes.
