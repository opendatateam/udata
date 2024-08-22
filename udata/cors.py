import logging

from flask import request
from werkzeug.datastructures import Headers

log = logging.getLogger(__name__)


def add_vary(headers: Headers, header: str):
    values = headers.getlist("Vary")
    if header not in values:
        values.append(header)
    headers.set("Vary", ", ".join(values))


def add_actual_request_headers(headers: Headers) -> Headers:
    origin = request.headers.get("Origin", None)
    add_vary(headers, "Origin")

    if origin:
        headers.set("Access-Control-Allow-Origin", origin)
        headers.set("Access-Control-Allow-Credentials", "true")

    return headers


def is_preflight_request() -> bool:
    return (
        request.method == "OPTIONS"
        and request.headers.get("Access-Control-Request-Method", None) is not None
    )


def is_allowed_cors_route():
    return (
        request.path.endswith((".js", ".css", ".woff", ".woff2", ".png", ".jpg", ".jpeg", ".svg"))
        or request.path.startswith("/api")
        or request.path.startswith("/oauth")
    )


def add_preflight_request_headers(headers: Headers) -> Headers:
    origin = request.headers.get("Origin", None)
    add_vary(headers, "Origin")

    if origin:
        headers.set("Access-Control-Allow-Origin", origin)
        headers.set("Access-Control-Allow-Credentials", "true")

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
