import logging

import requests
from flask import abort, current_app, make_response

from udata.api import API, apiv2
from udata.app import cache

log = logging.getLogger(__name__)

ns = apiv2.namespace("captchetat", "CaptchEtat related operations")
captchetat_parser = apiv2.parser()
captchetat_parser.add_argument(
    "get", type=str, location="args", help="type of data wanted from captchetat"
)
captchetat_parser.add_argument("c", type=str, location="args", help="captcha name")
captchetat_parser.add_argument(
    "t",
    type=str,
    location="args",
    help="this is a technical argument auto-generated for audio content",
)

CAPTCHETAT_ERROR = "CaptchEtat request didn't failed but didn't contain any access_token"


def bearer_token():
    """Get CaptchEtat bearer token from cache or get a new one from CaptchEtat Oauth server"""
    token_cache_key = current_app.config.get("CAPTCHETAT_TOKEN_CACHE_KEY")
    url = current_app.config.get("CAPTCHETAT_OAUTH_BASE_URL")
    previous_value = cache.get(token_cache_key)
    if previous_value:
        return previous_value
    log.debug(f"New access token requested from {url}")
    try:
        oauth = requests.post(
            f"{url}/api/oauth/token",
            data={
                "grant_type": "client_credentials",
                "scope": "piste.captchetat",
                "client_id": current_app.config.get("CAPTCHETAT_CLIENT_ID"),
                "client_secret": current_app.config.get("CAPTCHETAT_CLIENT_SECRET"),
            },
        )
        oauth.raise_for_status()
        body = oauth.json()
        access_token = body.get("access_token")
        if not access_token:
            raise requests.exceptions.RequestException(CAPTCHETAT_ERROR)
        cache.set(token_cache_key, access_token, timeout=body.get("expires_in", 0))
    except requests.exceptions.RequestException as request_exception:
        log.exception(f"Error while getting access token from {url}")
        raise request_exception
    else:
        return access_token


@ns.route("/", endpoint="captchetat")
class CaptchEtatAPI(API):
    @apiv2.expect(captchetat_parser)
    @apiv2.doc("captchetat")
    def get(self):
        """CaptchEtat endpoint for captcha generation and validation"""
        args = captchetat_parser.parse_args()
        try:
            token = bearer_token()
            headers = {}
            if token:
                headers = {"Authorization": "Bearer " + token}
            captchetat_url = current_app.config.get("CAPTCHETAT_BASE_URL")
            req = requests.get(
                f"{captchetat_url}/simple-captcha-endpoint", headers=headers, params=args
            )
            req.raise_for_status()
        except requests.exceptions.RequestException:
            abort(500, description="Catptcha internal error")

        resp = make_response(bytes(req.content))
        resp.headers["Content-Type"] = req.headers.get("Content-Type")
        return resp
