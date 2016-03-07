# uData

[![Python Requirements Status][requires-io-badge]][requires-io-url]
[![JavaScript Dependencies Status][david-dm-badge]][david-dm-url]
[![JavaScript Development Dependencies Status][david-dm-dev-badge]][david-dm-dev-url]
[![Join the chat at https://gitter.im/etalab/udata][gitter-badge]][gitter-url]


_uData_ is an open and social data hub.

## Compatibility

udata requires Python 2.7, MongoDB 3.2+, ElasticSearch 1.7 and Redis.

## Installation

### System dependencies

```shell
sudo apt-get install -y --no-install-recommends tar git wget curl build-essential pkg-config  python python-dev python-pip libjpeg-dev zlib1g-dev libpng12-dev libtiff5-dev libfreetype6-dev liblcms2-dev libopenjpeg-dev libwebp-dev libpng12-dev libxml2-dev libxslt1-dev liblzma-dev libyaml-dev && sudo pip install virtualenv cython
```

!!! note
    MacOSX: checkout Homebrew for installing dependencies.

### Installing the project

Let's call the root project `$WORKSPACE`.

```shell
mkdir $WORKSPACE && cd $_
```

Retrieve the sources

```shell
git clone https://github.com/etalab/udata.git
```

Install your [virtualenv][]

```shell
virtualenv --python=python2.7 venv
source venv/bin/activate
pip install -r udata/requirements/develop.pip
```

### Installing 3rd party services

The project depends on ElasticSearch, Redis and MongoDB. We will use [docker-compose][] to manage all that.
[Install Docker-Compose for your system][docker-compose-install].
On linux you should also [create a _docker_ group][docker-compose-group].
On Windows and MacOSX you will have to using a [docker-machine][].

Then start the services:

```shell
cd udata
docker-compose up
```

On the very first run it will download and install images which takes a while.

!!! warning
    Test your _docker-compose_ is running successfully entering `curl http://locahost:9200`.
    It should output a JSON search response.
    If you have no output at all for too long,
    check the [IPv6 possible issue](https://github.com/docker/docker/issues/2174#issuecomment-35697655).

#### Installing natively

If you really don't want to use docker you can install MongoDB 3.2,
ElasticSearch 1.7 with analysis-icu plugin, and Redis 3.0 on your way.

Now open your browser to http://localhost:7000/. It's empty and ugly, yet it works!

## JS dependencies

You need NodeJS 4.2. If it's not already installed or you have a different version,
you should consider [installing NVM][nvm-install].

Then install JavaScript dependencies

```shell
cd udata
npm install
```

### Building CSS (and JS)

To build the CSS run in a dedicated terminal:

```shell
npm run assets:watch
```

Visit http://localhost:7000 again. It should look better!

## Documentation

The full documentation is hosted [on Read the Docs][official-doc].

## Translations

```shell
inv i18n && tx push -s && tx pull -f && inv i18nc
```

You have to set a [~/.transifexrc][transifexrc] first.

[docker-compose]: https://docs.docker.com/compose/
[docker-compose-install]: https://docs.docker.com/compose/install/
[docker-compose-group]: https://docs.docker.com/engine/installation/linux/ubuntulinux/#create-a-docker-group
[docker-machine]: https://docs.docker.com/machine/overview/
[official-doc]: https://udata.readthedocs.org/
[transifexrc]: http://docs.transifex.com/client/config/
[virtualenv]: https://virtualenv.readthedocs.org/
[nvm-install]: https://github.com/creationix/nvm#installation

[requires-io-url]: https://requires.io/github/etalab/udata/requirements/?branch=master
[requires-io-badge]: https://requires.io/github/etalab/udata/requirements.png?branch=master
[david-dm-url]: https://david-dm.org/etalab/udata
[david-dm-badge]: https://img.shields.io/david/etalab/udata.svg
[david-dm-dev-url]: https://david-dm.org/etalab/udata#info=devDependencies
[david-dm-dev-badge]: https://david-dm.org/etalab/udata/dev-status.svg
[gitter-badge]: https://badges.gitter.im/Join%20Chat.svg
[gitter-url]: https://gitter.im/etalab/udata
