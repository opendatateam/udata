# Development

There is many way to intall a development environement for uData.
The prefered one is to use virtualenv and Docker/Docker-Compose.

## System dependencies

The uData development environment requires the following system dependencies
(on an Debian/APT based system):

* build-essential
* pkg-config
* python-dev
* python-virtualenv
* libjpeg-dev
* zlib1g-dev
* libpng12-dev
* libtiff5-dev
* libfreetype6-dev
* liblcms2-dev
* libopenjpeg-dev
* libwebp-dev
* libpng12-dev
* libxml2-dev
* libxslt1-dev
* liblzma-dev

```shell
apt-get install build-essential pkg-config python-dev python-virtualenv libjpeg-dev zlib1g-dev libpng12-dev libtiff5-dev libfreetype6-dev liblcms2-dev libopenjpeg-dev libwebp-dev libpng12-dev libxml2-dev libxslt1-dev liblzma-dev
```

## Python dependencies

It is recommanded to work within a virtualenv to ensure proper dependencies isolation.

It is recommanded to have a parent workspace where project are cloned, data stored...
It will be designated by `$WORKSPACE` until the end of the documentation.

```shell
$ mkdir $WORKSPACE && cd $WORKSPACE
```

First, create and activate your virtualenv, with one of the following command
(depending on you using virtualenv or virtualenvwrapper):

```shell
$ virtualenv . && source bin/activate  # for virtualenv
$ mkvirtualenv udata && setvirtualenvproject .  # for virtualenvwrapper
$ mkproject udata  # for virtualenvwrapper with configured project dir
```

If your system is using Python 3 as primary Python installation,
don't forget to specify the python version with the `-p` parameter:

```shell
$ virtualenv -p /bin/python2 .
$ mkvirtualenv udata -p /bin/python2
$ mkproject -p /bin/python2 udata
```

Clone the uData project into your workspace:

```shell
$ git clone https://github.com/etalab/udata.git
```

Install the development dependencies and install the project as editable:

```shell
$ pip install -r udata/requirements/develop.pip
$ pip install --no-deps -e udata/
```

## Middleware installation

You can use native middleware packages or docker images (prefered method)

### The docker way

This is the prefered method as it does not depends of version provided by your OS.
You need to have [Docker] installed and working for your user.

You need to [install docker-compose]:

```shell
$ pip install docker-compose
```

A sample `docker-compose.yml` is provided in the udata repository.

```shell
$ cp udata/docker-compose.yml .
$ docker-compose pull  # Pull docker images
$ docker-compose up -d  # Run docker processes in background
$ docjer-compose ps  # List running docker processes
```

ElasticSearch requires the elasticsearch-icu-analysis to be able to sort
on unicode strings.
You need to look at the compatibility matrix to find the corresponding version
on [the official documention](https://github.com/elastic/elasticsearch-analysis-icu).
At the time this doc is written, we use ElasticSearch 1.4.3 and ElasticSearch ICU Analysis 2.4.2

```shell
$ docker-compose run search /bin/bash
$ /usr/share/elasticsearch/bin/plugin install elasticsearch/elasticsearch-analysis-icu/2.4.2
$ exit
$ docker-compose restart search
```

### The native way

In case you prefer native packages, you must ensure a sufficient versionning:

* ElasticSearch 1.4+
* MongoDB 2.6+
* Redis


## JavaScript dependencies

JavaScript dependencies are managed by npm and requires
webpack to be installed globaly.

```shell
$ sudo npm install -g webpack
```

Then, to fetch the udata dependencies:

```shell
$ cd $WORKSPACE/udata
$ npm install
```

From here you can build the assets in production mode once and for all:

```shell
$ inv assets
```

or use the watch process which will trigger a build each time a javascript file
or a less file is touched:

```shell
$ inv watch
```

## Working

### The udata launcher

As you installed uData as editable it provides the `udata` launcher on your virtualenv path.

```shell
$ udata -?
```

For developement purpose, you can use the `manage.py` launcher which provides the same commands but in debug mode.

```shell
$ python udata/manage.py -?
```

You can optionnaly specify a configuration file by exporting the `UDATA_SETTINGS` environment variable:

```shell
$ export UDATA_SETTINGS=$WORKSPACE/udata.cfg
```

For more details on the configuration file,
see [configuration documentation](configuration.md)


### Initialization

You need to initialize some data before starting udata.

```shell
# Initialize database, indexes...
$ udata init
# Fetch and load licenses
$ udata licenses https://www.data.gouv.fr/api/1/datasets/licenses
$ cd $WORKSPACE/udata
# Fetch last translations
$ tx pull
# Compile translations
$ inv i18nc
```

### Running the processes

uData requires at least 3 processes:

* a frontend process
* a worker process
* a beat process (for scheduled tasks)

A Procfile is provided to ease the task.
You can use [Honcho] (or whatever Procfile manager) to run the 3 processes
in your development environement.

```shell
$ honcho start
```

### Common tasks

Most of the common and recurrent tasks are automatised with invoke.

In the udata directory, you can:

```shell
# List all the available tasks
$ inv -l
Available tasks:

  beat    Run celery beat process
  clean   Cleanup all build artifacts
  cover   Run tests suite with coverage
  dist    Package for distribution
  doc     Build the documentation
  i18n    Extract translatable strings
  i18nc   Compile translations
  qa      Run a quality report
  serve   Run a development server
  test    Run tests suite
  work    Run a development worker

# Build the documentation
$ inv doc
# Run the tests
$ inv test
```


[Docker]: https://www.docker.com/
[install docker-compose]: https://docs.docker.com/compose/install/
[Honcho]: https://github.com/nickstenning/honcho
