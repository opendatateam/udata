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

You can now log into this account to install uData:

```shell
$ su - udata
$ pwd
/srv/udata
```

## Python and virtual environment

It is recommended to work within a virtualenv to ensure proper dependencies isolation.
If you're not familiar with that concept, read [Python Virtual Environments - a Primer][].

We create a virtualenv in the udata home directory so it is activated each time
you log into its account:

```shell
$ virtualenv --python=python2.7 $HOME
$ source bin/activate  
$ pip install Cython  # Enable optimizations on some packages
$ pip install udata
```
You can also install the extensions you want:

```shell
$ pip install udata-piwik
```

!!! note
    We install Cython before all other dependencies because
    some have an optionnal compilation support for Cython
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

## Sample NGinx & uWSGI configuration

You can use whatever stack you want to run uData, NGinx or Apache 2 as reverse proxy, supervisord + GUnicorn or uWSGI...

All you need to remember is that uData requires at least 3 services to run:
- a web frontend using the `udata.wsgi` WSGI entry point.
- a worker service using celery
- a beat/cron service using celery too

We give you an example using [NGinx][] + [uWSGI][] to run these 3 parts,
expose the frontend on the `data.example.com` domain
(and having the middlewares running on the same host)

Install NGinx and uWSGI with root privileges:

```shell
$ apt-get install nginx-full uwsgi uwsgi-plugin-python
```

Let's start with the uwsgi configuration files. We write 3 ini files, one for each service.

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

; Disable write exception when NGinx timed out before uwsgi response
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

**`/etc/uwsgi/apps-available/udata-worker.ini`**

```inifile
##
# uWSGI configuration for data.example.com worker
##

[uwsgi]
master = true
plugin = python
home = /srv/udata
chdir = %(home)
virtualenv = %(home)
pythonpath = %(home)/bin
socket = /tmp/udata-worker.sock
chmod-socket = 666
processes = 1
uid = udata
gid = www-data
smart-attach-daemon = /tmp/celery-worker.pid %(home)/bin/celery -A udata.worker worker --pidfile=/tmp/celery-worker.pid
exec-as-user-atexit = kill -TERM `cat /tmp/celery-worker.pid`
```
**`/etc/uwsgi/apps-available/udata-beat.ini`**

```inifile
##
# uWSGI configuration for data.example.com beat
##

[uwsgi]
master = true
plugin = python
home = /srv/udata
chdir = %(home)
virtualenv = %(home)
pythonpath = %(home)/bin
socket = /tmp/udata-beat.sock
chmod-socket = 660
processes = 1
uid = udata
gid = www-data
smart-attach-daemon = /tmp/celery-beat.pid %(home)/bin/celery -A udata.worker beat --pidfile=/tmp/celery-beat.pid
exec-as-user-atexit = kill -TERM `cat /tmp/celery-beat.pid`
```

Then create symlinks to activate these configurations:

```shell
$ ln -s /etc/uwsgi/apps-{available,enabled}/udata-front.ini
$ ln -s /etc/uwsgi/apps-{available,enabled}/udata-worker.ini
$ ln -s /etc/uwsgi/apps-{available,enabled}/udata-beat.ini
```

Then define a NGinx server host configuration in `/etc/nginx/sites-availables/data.example.com`:

```nginx
##
# NGinx configuration for data.example.com
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
            expires 1M;
        }

        location ~ /_themes/ {
            expires 1M;
        }

        location ~ /s/ {
            # Resources are stored separately
            alias /srv/udata/fs/;
            # Disable disk buffering for downloads
            proxy_max_temp_file_size 0;
            expires 1M;

            add_header 'Access-Control-Allow-Origin' '*';
            add_header 'Access-Control-Allow-Methods' 'GET, OPTIONS';
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
    }
}
```

Then create a symlink to activate it:

```shell
$ ln -s /etc/nginx/sites-{available,enabled}/data.example.com
```

Before restarting all services to start uData, we need to adjust its configuration
and collect static assets to make them available for NGinx.

```shell
su - udata
```

Edit your `udata.cfg` configuration with these parameters:

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

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

# Optionnaly activate some installed plugins
PLUGINS = (
    'piwik',
)

# Optionnaly activate an installed theme
THEME = 'my-theme'

# Define where resources are stored and exposed
FS_ROOT = '/srv/udata/fs'
FS_PREFIX = '/s'
```

You can now process static assets in the directory declared in the NGinx configuration (ie. `/srv/udata/public`):

```shell
$ udata collect -ni $HOME/public
```

Alrigth, everything is ready to run udata so logout from the `udata` and restart NGinx and uWSGI:

```shell
$ service uwsgi restart
$ service nginx restart
```
And then go see your awesome open data portal on <http://data.example.com>.

[uwsgi]: https://uwsgi-docs.readthedocs.io/
[nginx]: https://nginx.org/
[install-virtualenv]: https://virtualenv.pypa.io/en/latest/installation.html
[Python Virtual Environments - a Primer]: https://realpython.com/blog/python/python-virtual-environments-a-primer/
