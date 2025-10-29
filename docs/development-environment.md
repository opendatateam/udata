# Advanced development environment

## System requirements

See [System dependencies](system-dependencies.md) for base system requirements.

See [getting-started](getting-started.md) for installation instructions.

### Dependency management

We're using `pyproject.toml` to manage our dependencies with optional dependency groups for different use cases.

**This is not mandatory unless you're actively contributing to the project.**

```shell
$ pre-commit install
```

Dependencies are defined in `pyproject.toml` with the following optional groups:
- `dev`: Development tools (ruff, pre-commit, invoke, etc.)
- `test`: Testing dependencies (pytest, mock, etc.)
- `doc`: Documentation dependencies (mkdocs, etc.)
- `report`: Reporting dependencies (coverage, flake8, etc.)

To install the project with all development dependencies:
```shell
uv sync --extra dev
```
...or, with pip:
```shell
pip install -e ".[dev]"
```

To install with specific optional dependencies:
```shell
uv sync --extra test         # For testing
uv sync --extra doc          # For documentation
uv sync --extra report       # For reporting
```
...or, with pip:
```shell
pip install -e ".[test]"     # For testing
pip install -e ".[doc]"      # For documentation
pip install -e ".[report]"   # For reporting
```

If you need to add or modify a dependency, edit the `pyproject.toml` file directly in the appropriate section.


### Optmizing performances with Cython

Some dependencies have an optional compilation support for Cython
resulting in better performances (mostly XML harvesting).
To enable it, you need to install Cython before all other dependencies:

```shell
$ pip install Cython
$ pip install -e ".[dev]"
```

### Mac OS caveats

#### Package installation fails

If installing `cryptography` fails:

```
brew install openssl@1.1
export LDFLAGS="-L$(brew --prefix openssl@1.1)/lib"
export CPPFLAGS="-I$(brew --prefix openssl@1.1)/include"
pip install -e ".[dev]"
```

If installing `Pillow` fails:

```
brew install libjpeg
pip install -e ".[dev]"
```

#### Local web server is slow

If you're using `{something}.local` as your `SITE_NAME`, you need to add an ipv6 resolution to this FQDN:

```
127.0.0.1   dev.local
::1         dev.local
```

[Reference and context here](https://superuser.com/a/1596341).

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
simply provide some fixes to [the translations](adding-translations.md)
or [the documentation](building-documentation.md).


[Python Virtual Environments - a Primer]: https://realpython.com/blog/python/python-virtual-environments-a-primer/
[dev-server]: http://localhost:7000/
[git]: https://git-scm.com/
[github]: https://github.com/opendatateam/udata
[new issue]: https://github.com/opendatateam/udata/issues/new
[homebrew]: http://brew.sh/
[invoke]: http://www.pyinvoke.org/
[install-virtualenv]: https://virtualenv.pypa.io/en/latest/installation.html
[nvm-install]: https://github.com/creationix/nvm#installation
