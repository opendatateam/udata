import logging
from urllib.parse import urlsplit

from flask import current_app, request
from werkzeug.datastructures import Headers

log = logging.getLogger(__name__)


def add_vary(headers: Headers, header: str):
    values = headers.getlist("Vary")
    if header not in values:
        values.append(header)
    headers.set("Vary", ", ".join(values))


def get_allowed_origins() -> set[str]:
    """Origins allowed to make *credentialed* cross-origin requests.

    The trusted front-end (cdata) is derived from `CDATA_BASE_URL` so it works
    out of the box, and operators can declare extra origins via
    `CORS_ALLOWED_ORIGINS`.
    """
    origins = set(current_app.config.get("CORS_ALLOWED_ORIGINS") or [])

    cdata_base_url = current_app.config.get("CDATA_BASE_URL")
    if cdata_base_url:
        parts = urlsplit(cdata_base_url)
        if parts.scheme and parts.netloc:
            origins.add(f"{parts.scheme}://{parts.netloc}")

    return origins


def set_allow_origin_headers(headers: Headers, origin: str) -> None:
    if origin in get_allowed_origins():
        # Trusted front-end: allow credentialed requests so the session cookie
        # can be sent and read cross-origin.
        headers.set("Access-Control-Allow-Origin", origin)
        headers.set("Access-Control-Allow-Credentials", "true")
    else:
        # Any other origin only gets anonymous access. Reflecting an arbitrary
        # origin together with `Allow-Credentials: true` is what would, in
        # theory, let a malicious site read a logged-in user's private data or
        # act on their behalf. In practice the session cookie is `SameSite=Lax`,
        # so browsers don't send it on cross-site requests anyway; this stricter
        # CORS policy is defense in depth so the protection doesn't rely on that
        # single browser-enforced mechanism.
        headers.set("Access-Control-Allow-Origin", "*")


def add_actual_request_headers(headers: Headers) -> Headers:
    origin = request.headers.get("Origin", None)
    add_vary(headers, "Origin")

    if origin:
        set_allow_origin_headers(headers, origin)

    return headers


def is_preflight_request() -> bool:
    return (
        request.method == "OPTIONS"
        and request.headers.get("Access-Control-Request-Method", None) is not None
    )


def is_allowed_cors_route():
    path: str = request.path

    # Allow to keep clean CORS when `udata` and the frontend are on the same domain
    # (as it's the case in data.gouv with cdata/udata).
    if not current_app.config["SECURITY_SPA_ON_SAME_DOMAIN"] and (
        path.startswith(current_app.config["SECURITY_LOGIN_URL"])
        or path.startswith(current_app.config["SECURITY_LOGOUT_URL"])
        or path.startswith(current_app.config["SECURITY_RESET_URL"])
        or path.startswith(current_app.config["SECURITY_REGISTER_URL"])
        or path.startswith(current_app.config["SECURITY_CONFIRM_URL"])
        or path.startswith(current_app.config["SECURITY_CHANGE_URL"])
        or path.startswith(current_app.config["SECURITY_CHANGE_EMAIL_URL"])
        or path.startswith(current_app.config["SECURITY_GET_CSRF"])
        or path.startswith(current_app.config["SECURITY_TWO_FACTOR_SETUP_URL"])
        or path.startswith(current_app.config["SECURITY_TWO_FACTOR_TOKEN_VALIDATION_URL"])
        or path.startswith(current_app.config["SECURITY_TWO_FACTOR_RESCUE_URL"])
        or path.startswith(current_app.config["SECURITY_VERIFY_URL"])
        or path.startswith("/oauth")
    ):
        return True

    return (
        path.endswith((".js", ".css", ".woff", ".woff2", ".png", ".jpg", ".jpeg", ".svg"))
        or path.startswith("/api")
        or path.startswith("/oauth/token")
        or path.startswith("/oauth/revoke")
        or path.startswith("/datasets/r/")
    )


def add_preflight_request_headers(headers: Headers) -> Headers:
    origin = request.headers.get("Origin", None)
    add_vary(headers, "Origin")

    if origin:
        set_allow_origin_headers(headers, origin)

        # The API allows all methods, so just copy the browser requested methods from the request headers.
        headers.set(
            "Access-Control-Allow-Methods", request.headers.get("Access-Control-Request-Method", "")
        )
        add_vary(headers, "Access-Control-Request-Method")

        headers.set(
            "Access-Control-Allow-Headers",
            request.headers.get("Access-Control-Request-Headers", ""),
        )
        add_vary(headers, "Access-Control-Request-Headers")

    return headers


def init_app(app):
    """
    The CORS should be enabled before routing to trigger before some redirects.

        For OPTIONS requests, we do not call the backend API code at all.
    We just return the access-control headers.

    For other requests, we append the access-control headers to the original
    response.

    This module is inspired by:
    - the CORS logic https://github.com/fruitcake/php-cors/blob/master/src/CorsService.php
    - the middleware https://github.com/laravel/framework/blob/11.x/src/Illuminate/Http/Middleware/HandleCors.php
    """

    @app.before_request
    def bypass_code_for_options_requests():
        if not is_allowed_cors_route():
            return

        if is_preflight_request():
            headers = add_preflight_request_headers(Headers())
            return "", 204, headers

    @app.after_request
    def add_cors_headers(response):
        if not is_allowed_cors_route():
            return response

        if request.method == "OPTIONS":
            add_vary(response.headers, "Access-Control-Request-Method")

        add_actual_request_headers(response.headers)

        return response
