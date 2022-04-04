# Advanced development environment

## System requirements

See [System dependencies](system-dependencies.md) for base system requirements.

See [getting-started](getting-started.md) for installation instructions.

### Dependency management

We're using [pip-tools](https://github.com/jazzband/pip-tools/#pip-tools--pip-compile--pip-sync) with [a pre-commit hook](https://github.com/jazzband/pip-tools/#version-control-integration) to help us manage our requirements.

**This is not mandatory unless you're actively contributing to the project.**

```shell
$ pre-commit install
```

`pip-tools` uses the `.in` files in `requirements/` as input to generate the `.pip` files we rely on to install `udata`.

If you need to add or modify a dependency, do it in the `.in` files _and commit them_. The pre-commit hook will compile the `.pip` files and warn you.

You can also generate the `.pip` files manually from the `.in` files without commiting them beforehand. For example, if you modified `install.in`:

```shell
pip-compile requirements/install.in --output-file requirements/install.pip
```

### Optmizing performances with Cython

Some dependencies have an optional compilation support for Cython
resulting in better performances (mostly XML harvesting).
To enable it, you need to install Cython before all other dependencies:

```shell
$ pip install Cython
$ pip install -r requirements/develop.pip
$ pip install -e .
```

### Macos Big Sur caveat

If installing `cryptography` fails:

```
brew install openssl
export LDFLAGS="-L/usr/local/opt/openssl@1.1/lib"
export CPPFLAGS="-I/usr/local/opt/openssl@1.1/include"
pip install -r requirements/develop.pip
```

If installing `Pillow` fails:
```
brew install libjpeg
pip install -r requirements/develop.pip
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
$ inv oembed-watch # Continously watch and build oembed
```

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
[new issue]: https://github.com/opendatateam/udata/issues/new
[homebrew]: http://brew.sh/
[invoke]: http://www.pyinvoke.org/
[install-virtualenv]: https://virtualenv.pypa.io/en/latest/installation.html
[nvm-install]: https://github.com/creationix/nvm#installation
