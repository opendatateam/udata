# System dependencies

## Python requirements

udata requires [Python][] 3.11, 3.12, or 3.13 (see `requires-python` in `pyproject.toml`), its development tools and some libraries to be installed (with their headers).
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
    * libyaml (not mandatory but speeds up the yaml processing)
    * libffi (required by bcrypt)

### Debian/Ubuntu

On any Debian-like system you can install the development tools and libraries with:

```shell
$ apt-get install build-essential pkg-config python python-dev python-pip python-virtualenv\
    libjpeg-dev zlib1g-dev libtiff5-dev libfreetype6-dev \
    liblcms2-dev libopenjpeg-dev libwebp-dev libpng12-dev \
    libxml2-dev  libxslt1-dev liblzma-dev libyaml-dev libffi-dev
```

### MacOS/Homebrew

On MacOS with [Homebrew][], you can install the development tools and libraries with:

```shell
$ brew install automake autoconf libtool pkg-config python \
    libjpeg zlib libtiff freetype littlecms openjpeg webp libpng \
    libxml2 libxslt xz libyaml
```

## MongoDB and Redis

The project requires [MongoDB][] 6.0 or later and [Redis][].

!!! warning
    Please ensure you install compatible versions. Using unsupported versions may cause issues.

Installation steps vary depending on your operating system and configuration.
If you encounter any problems during installation, please reach out via [a GitHub issue][github-new-issue] or [a GitHub discussion][github-discussions].

### Redis

On Debian, as root:

```shell
$ apt-get install redis-server
```

### MongoDB

For Debian/Ubuntu, follow the [official MongoDB installation guide][mongo-install-instructions] for your distribution.

For a quick setup on Debian/Ubuntu (as root):

```shell
# Import the MongoDB public GPG key
$ curl -fsSL https://pgp.mongodb.com/server-6.0.asc | gpg -o /usr/share/keyrings/mongodb-server-6.0.gpg --dearmor

# Add MongoDB repository (adjust for your distribution)
$ echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-6.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-6.0.list

$ apt-get update
$ apt-get install -y mongodb-org
$ systemctl start mongod
$ systemctl enable mongod
```

!!! note
    The repository URL above is for Ubuntu 22.04 (Jammy). For other distributions, see the [official MongoDB installation instructions][mongo-install-instructions].

[mongodb]: https://www.mongodb.org/
[redis]: http://redis.io/
[homebrew]: http://brew.sh/
[python]: https://www.python.org/
[mongo-install-instructions]: https://www.mongodb.com/docs/manual/installation/
[github-discussions]: https://github.com/opendatateam/udata/discussions/2721
[github-new-issue]: https://github.com/opendatateam/udata/issues/new
