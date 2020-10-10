# Development environment

## System requirements

See [System dependencies](system-dependencies.md) for base system requirements.

An alternative way to use middlewares (ie. ElasticSearch, Redis, MongoDB) is provided
for getting started easily so it's not mandatory to install those natively.
See [Middlewares](#middlewares) for details.

## Retrieving the sources

You also will need [Git][] to fetch sources and publish your contributions.
If you use a Debian-like distribution with `apt-get`, the package is named `git-core`.
If you prefer [Homebrew][] (OSX), the package is named `git`.

The sources of the project are on [Github][]:

```shell
$ git clone https://github.com/opendatateam/udata.git
```

(or clone your own fork if you plan to [contribute](contributing-guide.md))

## Middlewares

We will use [docker-compose][] to manage all that.
[Install Docker-Compose for your system][docker-compose-install]
then start the services:

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

## Python and virtual environment

It is recommended to work within a virtualenv to ensure proper dependencies isolation.
If you're not familiar with that concept, read [Python Virtual Environments - a Primer][].

Alright, now you can type these commands knowing what you are doing:

```shell
$ python3 -m venv venv
$ source venv/bin/activate
$ pip install -r requirements/develop.pip
$ pip install -e .
```

Some dependencies have an optional compilation support for Cython
resulting in better performances (mostly XML harvesting).
To enable it, you need to install Cython before all other dependencies:

```shell
$ pip install Cython
$ pip install -r requirements/develop.pip
$ pip install -e .
```

## NodeJS and modules

NodeJS is required to build or run the frontend. Please check the .nvmrc at the root of the repository to check the exact version of NodeJS you need.
you should consider [installing NVM][nvm-install] which uses the existing `.nvmrc`.

```shell
$ nvm install
$ nvm use
```

Then install JavaScript dependencies:

```shell
$ npm install
```

Once it's done, you should be able to run the build command for JS and CSS:

```shell
$ inv assets-build
$ inv widgets-build
```

!!! note
    The **watcher commands** `inv assets-watch` and `inv widgets-watch` will recompile on each save, and only the relevant parts.

## Running the project for the first time

You need to initialize some data before being able to use udata:

```shell
# Initialize database, indexes...
$ udata init

# Optionally fetch and load some licenses from another udata instance
$ udata licenses https://www.data.gouv.fr/api/1/datasets/licenses

# Compile translations
$ inv i18nc
```

You should be to start using and contributing to udata.

## Running the project

You can use [invoke][] to launch the application services
(you might want to have each one runnning in a terminal):

```shell
$ inv serve         # Start the development server

$ inv work          # Start a worker process
$ inv beat          # Start a scheduler process

$ inv assets-watch  # Continously watch and build assets
$ inv widgets-watch # Continously watch and build widgets
```

When you have the development server running,
you can open your browser to <http://localhost:7000>.
Everything should be up and running!

!!! note "Tell us what you think"
    You are always welcome to tell us about your experience _installing udata_.
    Get in touch with us via our [Gitter chatroom][Gitter] or by raising a [new issue][] on [GitHub][].

## Common tasks

Most of the common tasks are scripted in the `tasks.py` file (which is using [invoke][]).
You can get the documentation related to all tasks with:

```shell
$ inv -l
```

It might be required to update your Python and JavaScript dependencies to ensure compatibility.
A task is provided to automate it:

```shell
# Update dependencies
$ inv update

# Update dependencies and migrate data
$ inv update -m
```

It's advised to update your dependencies when you pull upstream changes or switch branch:

```shell
# Update dependencies, migrate data, recompile translations...
$ inv update -m i18nc
```

Now check out our advanced documentation for a focus on some specific tasks.
You may want to be able to [run the tests](testing-code.md) to for a backend contribution,
maybe [create a full theme](creating-theme.md)
or simply provide some fixes to [the translations](adding-translations.md)
or [the documentation](building-documentation.md).


[Python Virtual Environments - a Primer]: https://realpython.com/blog/python/python-virtual-environments-a-primer/
[dev-server]: http://localhost:7000/
[docker-compose-install]: https://docs.docker.com/compose/install/
[docker-compose]: https://docs.docker.com/compose/
[git]: https://git-scm.com/
[github]: https://github.com/opendatateam/udata
[gitter]: https://gitter.im/opendatateam/udata
[new issue]: https://github.com/opendatateam/udata/issues/new
[homebrew]: http://brew.sh/
[invoke]: http://www.pyinvoke.org/
[install-virtualenv]: https://virtualenv.pypa.io/en/latest/installation.html
[nvm-install]: https://github.com/creationix/nvm#installation
