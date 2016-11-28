# System dependencies

## Git

First of all, you need [Git][].

If you use a Debian-like distribution with `apt-get`, the package is named `git-core`.
If you prefer [Homebrew][] (OSX), the package is named `git`.

## Python requirements

uData requires [Python][] 2.7 (installed by default on OSX and many Linux distributions),
its development tools and some libraries to be installed (with their headers).
Most of them might already be installed as they are common development dependencies.
The full dependencies list is:

* Pillow (Image processing)
    * libjpeg
    * zlib
    * libpng
    * libtiff
    * libfreetype
    * liblcms2
    * libopenjpeg
    * libwebp
* lxml dependencies
    * libxml2
    * libxslt
* Misc dependencies
    * liblzma (required to load GeoZones)
    * libyaml (not mandatory but speed up the yaml processing)

### Debian/Ubuntu

On any Debian-like system you can install the development tools and libraries with:

```shell
$ apt-get install build-essential pkg-config python python-dev python-pip \
    libjpeg-dev zlib1g-dev libtiff5-dev libfreetype6-dev \
    liblcms2-dev libopenjpeg-dev libwebp-dev libpng12-dev \
    libxml2-dev  libxslt1-dev liblzma-dev libyaml-dev
```

### OSX/Homebrew

On Mac OSX with [Homebrew][], you can install the development tools and libraries with:

```shell
$ brew install automake autoconf libtool pkg-config python \
    libjpeg zlib libtiff freetype littlecms openjpeg webp libpng \
    libxml2 libxslt xz libyaml
```


## Retrieving the sources

The sources of the project are on [Github][]:

```shell
$ git clone https://github.com/opendatateam/udata.git
```


## MongoDB, ElasticSearch and Redis

The project depends on [MongoDB][] 3.2+, [ElasticSearch][] 2.4 and [Redis][].

Installing these dependencies can be cumbersome given you operating system.
That's why we made a Docker container to ease that step.
You can either use it or install these dependencies by hand with the appropriated versions.

### With Docker

We will use [docker-compose][] to manage all that.
[Install Docker-Compose for your system][docker-compose-install].
On linux you should also [create a _docker_ group][docker-compose-group].
On Windows and MacOSX you will have to use a [docker-machine][].

Then start the services:

```shell
$ cd udata
$ docker-compose up
```

On the very first run it will download and install Docker images which takes a while depending of your connection.

!!! warning
    Test your _docker-compose_ is running successfully entering `curl http://localhost:9200`.
    It should output a JSON search response.
    If you have no output at all for too long,
    check the [IPv6 possible issue](https://github.com/docker/docker/issues/2174#issuecomment-35697655).

And install the [analysis-icu][] plugin for ElasticSearch:

```shell
$ docker-compose run search plugin install analysis-icu
$ docker-compose restart search
```

### By hand

It will depend on your configuration, join us on [Gitter][] if you have any issue.

!!! note
    Match the Analysis ICU plugin version to your ElasticSearch version (2.4)
    given those indicated in [the official repository][analysis-icu]

For example if you are using [Homebrew][] (OSX):

```shell
$ brew install elasticsearch
$ /usr/local/Cellar/elasticsearch/2.4.1/libexec/bin/plugin install analysis-icu
```

Once all dependencies are installed by hand, you can launch these services manually or use [Honcho][] with the proposed Procfile at the root of the repository (you'll have to uncomment related lines).

But first, let's install [local dependencies](local-dependencies.md)!


[mongodb]: https://www.mongodb.org/
[elasticsearch]: https://www.elastic.co/products/elasticsearch
[redis]: http://redis.io/
[honcho]: https://github.com/nickstenning/honcho
[gitter]: https://gitter.im/opendatateam/udata
[github]: https://github.com/opendatateam/udata
[homebrew]: http://brew.sh/
[python]: https://www.python.org/
[git]: https://git-scm.com/
[docker-compose]: https://docs.docker.com/compose/
[docker-compose-install]: https://docs.docker.com/compose/install/
[docker-compose-group]: https://docs.docker.com/engine/installation/linux/ubuntulinux/#create-a-docker-group
[docker-machine]: https://docs.docker.com/machine/overview/
[analysis-icu]: https://github.com/elastic/elasticsearch-analysis-icu
