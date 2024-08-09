from flask import url_for
from flask_restx.reqparse import RequestParser

from udata.api import API, adminified_parser, api
from udata.forms import Form

from . import APITestCase

ns = api.namespace("fake-ns", "A Fake namespace")


@ns.route("/options", endpoint="fake-options")
class FakeAPI(API):
    def get(self):
        return {"success": True}


@ns.route("/fake-form", endpoint="fake-form")
class FakeFormAPI(API):
    def post(self):
        class FakeForm(Form):
            pass

        api.validate(FakeForm)
        return {"success": True}


class OptionsCORSTest(APITestCase):
    def test_should_allow_options_and_cors(self):
        """Should allow OPTIONS operation and give cors parameters"""
        response = self.client.options(
            url_for("api.fake-options"),
            headers={
                "Origin": "http://localhost",
                "Access-Control-Request-Method": "GET",
            },
        )

        self.assert204(response)
        self.assertEqual(response.headers["Access-Control-Allow-Origin"], "http://localhost")

        response = self.client.options(
            url_for("api.fake-options"),
            headers={
                "Origin": "http://localhost",
                "Access-Control-Request-Method": "GET",
                "Authorization": "Bearer YouWillNeverGuess",
                "Access-Control-Request-Headers": "Authorization",
            },
        )
        self.assertEqual(response.headers["Access-Control-Allow-Origin"], "http://localhost")
        self.assertEqual(response.headers["Access-Control-Allow-Headers"], "Authorization")
        self.assertEqual(response.headers["Access-Control-Allow-Methods"], "GET")


class JSONFormRequestTest(APITestCase):
    def test_non_json_content_type(self):
        """We expect JSON requests for forms and enforce it"""
        response = self.client.post(
            url_for("api.fake-form"), {}, headers={"Content-Type": "multipart/form-data"}
        )
        self.assert400(response)
        self.assertEqual(response.json, {"errors": {"Content-Type": "expecting application/json"}})

    def test_json_content_type(self):
        """We expect JSON requests for forms and enforce it"""
        response = self.post(url_for("api.fake-form"), {})
        self.assert200(response)


class ParserTest:
    def test_adminified_parser(self):
        parser = RequestParser()
        parser.add_argument("some_arg", type=int, default=42, location="args", help="foobar")
        parser.add_argument(
            "page_size", type=int, default=20, location="args", help="The page size to fetch"
        )
        adminified = adminified_parser(parser)
        # We still have all the arguments.
        assert len(adminified.args) == 2
        # We still have the default value of the `some_arg` argument.
        assert adminified.args[0].default == 42
        # But the default value of the `page_size` has been "adminified": set to None.
        assert adminified.args[1].default is None
