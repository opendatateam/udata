import pytest

from udata.auth.forms import ExtendedRegisterForm
from udata.core.user.forms import UserProfileForm

pytestmark = [pytest.mark.usefixtures("clean_db")]


def test_register_form_accepts_no_url():
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


def test_user_profile_form_accepts_no_url():
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
