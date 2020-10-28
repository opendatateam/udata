# Installation for production

This page document how to perform a native deployement on a Debian-like environment,
for a `udata` user with home in`/srv/udata`.
These steps require the [system dependencies](system-dependencies.md) to be installed.

# User and home dir creation

We want to create a `udata` user which primary group is `udata`,
member of the `www-data` group and having its home directory in `/srv/udata`:

```shell
$ useradd -m -d /srv/udata -G www-data udata
```

You can check the result with:

```shell
$ id udata
uid=1001(udata) gid=1001(udata) groups=33(www-data)
$ ls -l /srv
total 4
drwxr-xr-x 9 udata udata 4096 Jun 23 05:50 udata
```

You can now log into this account to install udata:

```shell
$ su - udata
$ pwd
/srv/udata
```

## Python and virtual environment

It is recommended to work within a virtualenv to ensure proper dependencies isolation.

We create a virtualenv in the `udata` home directory so it is activated each time
you log into its account:

```shell
$ python3 -m venv $HOME
$ . bin/activate
$ pip install Cython  # Enable optimizations on some packages
$ pip install --upgrade setuptools  # Make sure setuptools is up to date
$ pip install udata
```
You can also install the extensions you want:

```shell
$ pip install udata-piwik
```

!!! note
    We install Cython before all other dependencies because
    some have an optional compilation support for Cython
    resulting in better performances (mostly XML harvesting).


You can now create your configuration file:

```shell
$ touch udata.cfg
$ export UDATA_SETTINGS=/srv/udata/udata.cfg
```

To ease the `udata` client handling, you might want to export this
environment variable each time you login:

```shell
$ echo "export UDATA_SETTINGS=/srv/udata/udata.cfg" >> .profile
```

Then you need to put some configuration parameters in your file.
See [Adapting settings](adapting-settings.md) for details about the configuration file.

You're all set, you can now use the `udata` command line client to initialize the platform.
Just answer the questions:

```shell
$ udata init
```

## Sample nginx & uWSGI configuration

You can use whatever stack you want to run udata, nginx or Apache 2 as reverse proxy, supervisord + Gunicorn or uWSGI...

All you need to remember is that udata requires at least 3 services to run:

- a web frontend using the `udata.wsgi` WSGI entry point.
- a worker service using [celery][]
- a beat/cron service using [celery][] too

We give you an example for a `udata` user serving a `data.example.com` domain from `/srv/udata` on a single server with:

- [nginx][] + [uWSGI][] to run the frontend,
- systemd handling both the worker and the beat services,
- the middlewares running on the same host.


Install nginx and uWSGI with root privileges:

```shell
$ apt-get install nginx-full uwsgi uwsgi-plugin-python
```

Let's start with the uwsgi configuration file:

**`/etc/uwsgi/apps-available/udata-front.ini`**

```inifile
##
# uWSGI configuration for data.example.com front
##

[uwsgi]
master= true

; Python / Environment configuration
plugin = python
home = /srv/udata
chdir = %(home)
virtualenv = %(home)
pythonpath = %(home)/bin
module = udata.wsgi
callable = app

; Sockets and permissions
stats = /tmp/udata-front-stats.sock
socket = /tmp/udata-front.sock
chmod-socket = 664
uid = udata
gid = www-data

; Tune these values according to your environment
processes = 5
cpu-affinity = 1

; Disable requests logging
disable-logging = True

; Disable write exception when nginx timed out before uwsgi response
disable-write-exception = true

; Avoid PyMongo fork issue
; http://stackoverflow.com/questions/34369866/running-uwsgi-with-mongoengine
lazy-apps = true

; Recycle workers (tune according to you environment)
max-requests = 4000
reload-on-as = 512
reload-on-rss = 192
limit-as = 1024
no-orphans = true
vacuum = true
reload-mercy = 8
```

Then create the symlink to activate this configuration:

```shell
$ ln -s /etc/uwsgi/apps-{available,enabled}/udata-front.ini
```

You can now create the systemd unit file for Celery:

**`/etc/systemd/system/celery.service`**

```inifile
##
# A systemd unit file for udata celery services
#
# This launch 4 processes:
# - a beat service
# - a high queue consumer/worker
# - a default queue consumer/worker
# - a low queue consumer/worker
##

[Unit]
Description=udata celery services
After=network.target

[Service]
Type=forking
User=udata
WorkingDirectory=/srv/udata
LogsDirectory=udata-celery
RuntimeDirectory=udata-celery
ExecStart=/srv/udata/bin/celery multi start high default low \
  -c 1 -Q:high high -Q:default high,default -Q high,default,low \
  -A udata.worker --beat:1 \
  --pidfile=/var/run/udata-celery/worker-%%n.pid \
  --logfile=/var/log/udata-celery/worker-%%n%%I.log \
  --loglevel=INFO
ExecStop=/srv/udata/bin/celery multi stopwait high default low \
  --pidfile=/var/run/udata-celery/worker-%%n.pid \
ExecReload=/srv/udata/bin/celery multi restart worker \
  -A udata.worker --beat:1 \
  --pidfile=/var/run/udata-celery/worker-%%n.pid \
  --logfile=/var/log/udata-celery/worker-%%n%%I.log \
  --loglevel=INFO

[Install]
WantedBy=multi-user.target
```

**Note:** This unit file handle tasks priorities and beat.
Adapt it to your needs according to the [Celery daemonizing documentation](http://docs.celeryproject.org/en/latest/userguide/daemonizing.html).
You might need to allow more workers on a queue
or extract the beat service into its own unit if you have multiple workers.

Then load it into systemd and enable it:

```shell
$ systemctl daemon-reload
$ systemctl enable celery
```

Then define a nginx server host configuration in `/etc/nginx/sites-available/data.example.com`:

```nginx
##
# nginx configuration for data.example.com
##

## uWSGI
upstream uwsgi-udata {
    ip_hash;
    server unix:///tmp/udata-front.sock;
    keepalive 32;
}

server {
    listen 80;
    server_name data.example.com;

    access_log /var/log/nginx/data.example.com.access.log;
    error_log /var/log/nginx/data.example.com.error.log;

    client_max_body_size 0; # Disable max client body size

    root /srv/udata/public/;

    # Enable gzip compression
    gzip on;
    gzip_disable "msie6";
    gzip_min_length  1100;
    gzip_buffers  4 32k;
    gzip_types
        application/atom+xml
        application/javascript
        application/json
        application/rdf+xml
        application/rss+xml
        application/vnd.geo+json
        application/vnd.ms-fontobject
        application/x-font-ttf
        application/x-javascript
        application/xml
        font/opentype
        image/svg+xml
        image/x-icon
        text/css
        text/csv
        text/javascript
        text/plain
        text/xml;
    gzip_vary on;

    add_header Pragma public;
    add_header Cache-Control public;
    add_header Connection "keep-alive";

    location / {

        try_files $uri @wsgi;

        location ~ /static/ {
            include /etc/nginx/static-common.conf;
        }

        location ~ /_themes/ {
            include /etc/nginx/static-common.conf;
        }

        location ~ /s/ {
            # Resources are stored separately
            alias /srv/udata/fs/;
            # Disable disk buffering for downloads
            proxy_max_temp_file_size 0;

            include /etc/nginx/static-common.conf;
        }
    }

    location @wsgi {
        uwsgi_pass uwsgi-udata;
        include uwsgi_params;

        proxy_redirect     off;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Host $server_name;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}
```

Create the reusable static cache and CORS snippet in `/etc/nginx/static-common.conf`
(feel free to adjust values to your needs):

```nginx
##
#  Common options to properly serve udata static content.
#
#  This content as long cache duration and is accessible
#  by external JS (CORS)
#
#  This includes:
#   - udata assets (for external loading of embeds)
#   - theme assets (for external loading of embeds)
#   - uploaded content (direct access to resources)
##

# Cache static assets
expires 1M;

# Allow pre-flight requests
if ($request_method = OPTIONS) {
    add_header 'Access-Control-Allow-Origin' '*';
    add_header 'Access-Control-Allow-Methods' 'GET, OPTIONS';
    add_header 'Access-Control-Allow-Headers' 'Origin,Authorization,Accept,DNT,User-Agent,If-Modified-Since,Cache-Control,Content-Type,Range';
    add_header 'Access-Control-Allow-Credentials' 'true';
    #
    # Tell client that this pre-flight info is valid
    # for 20 days
    #
    add_header 'Access-Control-Max-Age' 1728000;
    # Returns a response on OPTIONS (enable pre-flight requests)
    add_header 'Content-Type' 'text/plain; charset=utf-8';
    add_header 'Content-Length' 0;
    return 204;
}

add_header 'Access-Control-Allow-Origin' '*';
add_header 'Access-Control-Allow-Methods' 'GET, OPTIONS';
add_header 'Access-Control-Allow-Headers' 'Origin,Authorization,Accept,DNT,User-Agent,If-Modified-Since,Cache-Control,Content-Type,Range';
add_header 'Access-Control-Allow-Credentials' 'true';
```

Then create a symlink to activate it:

```shell
$ ln -s /etc/nginx/sites-{available,enabled}/data.example.com
```

Before restarting all services to start udata, we need to adjust its configuration
and collect static assets to make them available for nginx.

```shell
su - udata
```

Edit your `udata.cfg` configuration with these parameters:

```python
DEBUG = False

SITE_ID = 'data.example.com'  # Used to store metrics and portal configuration
SITE_TITLE = 'My awesome open data portal'

SERVER_NAME = 'data.example.com'

SECRET_KEY = 'put-some-unique-and-secret-key-here-for-security'

MONGODB_HOST = 'mongodb://localhost:27017/udata'

ELASTICSEARCH_URL = 'localhost:9200'

BROKER_URL = 'redis://localhost:6379'
CELERY_RESULT_BACKEND = 'redis://localhost:6379'
CELERY_TASK_RESULT_EXPIRES = 86400

# We use Redis as caching backend but in a separate collection
CACHE_TYPE = 'redis'
CACHE_REDIS_URL = 'redis://localhost:6379/2'

# The identity used to send mails
MAIL_DEFAULT_SENDER = ('Open Data Portal', 'portal@data.example.com')

# Set you available languages
LANGUAGES = {
    'fr': 'Français',
    'en': 'English',
}
# Here is you default language
DEFAULT_LANGUAGE = 'fr'

# Optionally activate some installed plugins
PLUGINS = (
    'piwik',
)

# Optionally activate an installed theme
# THEME = 'my-theme'

# Define where resources are stored and exposed
FS_ROOT = '/srv/udata/fs'
FS_PREFIX = '/s'
```

You can now process static assets in the directory declared in the nginx configuration (ie. `/srv/udata/public`):

```shell
$ udata collect -ni $HOME/public
```

Alright, everything is ready to run udata so logout from the `udata` account and restart nginx and uWSGI:

```shell
$ service uwsgi restart
$ service celery restart
$ service nginx restart
```
And then go see your awesome open data portal on <http://data.example.com>.

[uwsgi]: https://uwsgi-docs.readthedocs.io/
[nginx]: https://nginx.org/
[celery]: http://www.celeryproject.org/
[install-virtualenv]: https://virtualenv.pypa.io/en/latest/installation.html
[Python Virtual Environments - a Primer]: https://realpython.com/blog/python/python-virtual-environments-a-primer/
