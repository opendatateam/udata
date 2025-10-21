from udata.auth.forms import ExtendedRegisterForm
from udata.core.user.forms import UserProfileForm
from udata.tests.api import PytestOnlyDBTestCase


class UserFormsTest(PytestOnlyDBTestCase):
    def test_register_form_accepts_no_url(self):
        form = ExtendedRegisterForm.from_json(
            {
                "email": "a@a.fr",
                "password": "passpass",
                "password_confirm": "passpass",
                "first_name": "azeaezr http://dumdum.fr",
                "last_name": "azeaze https://etalab.studio",
            }
        )
        form.validate()
        assert "first_name" in form.errors and "last_name" in form.errors

    def test_user_profile_form_accepts_no_url(self):
        form = UserProfileForm.from_json(
            {
                "email": "a@a.fr",
                "password": "passpass",
                "password_confirm": "passpass",
                "first_name": "azeaezr http://dumdum.fr",
                "last_name": "azeaze https://etalab.studio",
            }
        )
        form.validate()
        assert "first_name" in form.errors and "last_name" in form.errors
