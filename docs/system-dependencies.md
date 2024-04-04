# System dependencies

## Python requirements

udata requires [Python][] 3.7, its development tools and some libraries to be installed (with their headers).
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
    * libffi (required by bcrypt)

!!! note
    By the time this project was started, Python 3 did not have great third dependencies support
    and some requirements weren't suported yet so it was started with Python 2.7.

### Debian/Ubuntu

On any Debian-like system you can install the development tools and libraries with:

```shell
$ apt-get install build-essential pkg-config python python-dev python-pip python-virtualenv\
    libjpeg-dev zlib1g-dev libtiff5-dev libfreetype6-dev \
    liblcms2-dev libopenjpeg-dev libwebp-dev libpng12-dev \
    libxml2-dev  libxslt1-dev liblzma-dev libyaml-dev libffi-dev
```

### OSX/Homebrew

On Mac OSX with [Homebrew][], you can install the development tools and libraries with:

```shell
$ brew install automake autoconf libtool pkg-config python \
    libjpeg zlib libtiff freetype littlecms openjpeg webp libpng \
    libxml2 libxslt xz libyaml
```

## MongoDB and Redis

The project depends on [MongoDB][] 3.6+, and [Redis][]
(beware of the version, it will not work well if they are not respected).

The installation process is very specific to your operating system
and will depend on your configuration, join us via [a Github issue][github-new-issue] or via [a Github discussion][github-discussions] if you have any issue.

### Redis

On Debian, as root:

```shell
$ apt-get install redis-server
```

### MongoDB

On Debian Jessie (cf [mongo-install-instructions][] for other versions), as root:

```
$ apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv EA312927
$ echo "deb http://repo.mongodb.org/apt/debian jessie/mongodb-org/3.6 main" > /etc/apt/sources.list.d/mongodb-org-3.6.list
$ apt-get update
$ apt-get install -y mongodb-org
$ service mongod start
```

[mongodb]: https://www.mongodb.org/
[redis]: http://redis.io/
[homebrew]: http://brew.sh/
[python]: https://www.python.org/
[mongo-install-instructions]: https://docs.mongodb.com/v3.6/tutorial/install-mongodb-on-debian/#install-mongodb-community-edition
[github-discussions]: https://github.com/opendatateam/udata/discussions/2721
[github-new-issue]: https://github.com/opendatateam/udata/issues/new
