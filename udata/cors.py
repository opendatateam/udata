from werkzeug.datastructures import Headers
from flask import request

HEADER_API_KEY = 'X-API-KEY'

PREFLIGHT_HEADERS = (
    HEADER_API_KEY,
    'X-Fields',
    'Content-Type',
    'Accept',
    'Accept-Charset',
    'Accept-Language',
    'Authorization',
    'Cache-Control',
    'Content-Encoding',
    'Content-Length',
    'Content-Security-Policy',
    'Content-Type',
    'Cookie',
    'ETag',
    'Host',
    'If-Modified-Since',
    'Keep-Alive',
    'Last-Modified',
    'Origin',
    'Referer',
    'User-Agent',
    'X-Forwarded-For',
    'X-Forwarded-Port',
    'X-Forwarded-Proto',
)

def add_headers(headers):
    # Since we are an API, we accept all origins.
    headers.add("Access-Control-Allow-Origin", "*")

    headers.add("Access-Control-Allow-Headers", request.headers.get('Access-Control-Request-Headers', ''))
    # headers.add("Access-Control-Allow-Headers", ','.join(PREFLIGHT_HEADERS))
    headers.add("Access-Control-Allow-Credentials", "true")

    # The API allows all methods, so just copy the browser requested methods from the request headers.
    headers.add("Access-Control-Allow-Methods", request.headers.get('Access-Control-Request-Method', ''))

    return headers

def init_app(app):
    '''
    For OPTIONS requests, we do not call the backend API code at all.
    We just return the access-control headers.

    For other requests, we append the access-control headers to the original
    response.

    This module is inspired by:
    - the CORS logic https://github.com/fruitcake/php-cors/blob/master/src/CorsService.php
    - the middleware https://github.com/laravel/framework/blob/11.x/src/Illuminate/Http/Middleware/HandleCors.php
    '''
    @app.before_request
    def bypass_code_for_options_requests():
        if request.method == 'OPTIONS':
            headers = add_headers(Headers())
            return '', 204, headers

    @app.after_request
    def add_cors_headers(response):
        add_headers(response.headers)

        return response
