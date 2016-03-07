uData
=====

[![Build status](https://secure.travis-ci.org/etalab/udata.png)](https://coveralls.io/repos/etalab/udata/badge.png?branch=master)
[![Code coverage](https://coveralls.io/repos/etalab/udata/badge.png?branch=master)](https://coveralls.io/repos/etalab/udata/badge.png?branch=master)
[![Python Requirements Status](https://requires.io/github/etalab/udata/requirements.png?branch=master)](https://requires.io/github/etalab/udata/requirements/?branch=master)
[![JavaScript Dependencies Status](https://david-dm.org/etalab/udata.svg)](https://david-dm.org/etalab/udata)
[![Join the chat at https://gitter.im/etalab/udata](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/etalab/udata?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

_uData_ is an open and social data hub.


Compatibility
-------------

udata requires Python 2.7, MongoDB 3.2+, ElasticSearch 1.7 and Redis.


Installation
------------

### System dependencies

sudo apt-get install -y --no-install-recommends tar git wget curl build-essential pkg-config  python python-dev python-pip libjpeg-dev zlib1g-dev libpng12-dev libtiff5-dev libfreetype6-dev liblcms2-dev libopenjpeg-dev libwebp-dev libpng12-dev libxml2-dev libxslt1-dev liblzma-dev libyaml-dev && sudo pip install virtualenv cython

> MacOSX: checkout Homebrew for installing dependencies.


### Installing the project

Let's call the root project `$WORKSPACE`.

    mkdir $WORKSPACE && cd $_

Retrieve the sources

    git clone https://github.com/etalab/udata.git

Install your [virtualenv](https://virtualenv.readthedocs.org/en/latest/)

    virtualenv --python=python2.7 venv
    source venv/bin/activate
    pip install -r udata/requirements/develop.pip


### Installing 3rd party services

The project depends on ElasticSearch, Redis and MongoDB. We will use [docker-compose](https://docs.docker.com/compose/) to manage all that.
[Install Docker-Compose for your system](https://docs.docker.com/compose/install/). On linux you should also [create a _docker_ group](https://docs.docker.com/engine/installation/linux/ubuntulinux/#create-a-docker-group). On Windows and MacOSX you will have to using a [docker-machine](https://docs.docker.com/machine/overview/).

Then start the services:

    cd udata
    docker-compose up

On the very first run it will download and install images which takes a while.

> Test your _docker-compose_ is running successfully entering `curl http://locahost:9200` It should output a JSON search response. If you have no output at all for too long, check the [IPv6 possible issue](https://github.com/docker/docker/issues/2174#issuecomment-35697655).

And install the _analysis-icu_ plugin for ElasticSearch:

    docker-compose run search plugin install elasticsearch/elasticsearch-analysis-icu/2.7.0


#### Installing natively

If you really don't want to use docker you can install MongoDB 3.2, ElasticSearch 1.7 with analysis-icu plugin, and Redis 3.0 on your way.

Now open your browser to http://localhost:7000/. It's empty and ugly, yet it works!

## JS dependencies

You need NodeJS 4.2. If it's not already installed or you have a different version, you should consider [installing NVM](https://github.com/creationix/nvm#installation).


Then install JavaScript dependencies

    cd udata
    npm install


### Building CSS (and JS)

To build the CSS run in a dedicated terminal:

    npm run assets:watch

Visit http://localhost:7000 again. It should look better!


Documentation
-------------

The full documentation is hosted [on Read the Docs](http://udata.readthedocs.org/en/latest/).


Translations
------------

    inv i18n && tx push -s && tx pull -f && inv i18nc

You have to set a [~/.transifexrc](http://docs.transifex.com/client/config/) first.
