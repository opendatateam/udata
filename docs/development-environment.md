# Advanced development environment

## System requirements

See [System dependencies](system-dependencies.md) for base system requirements.

See [getting-started](getting-started.md) for installation instructions.

### Dependency management

Dependencies are defined in [`pyproject.toml`](https://github.com/opendatateam/udata/blob/main/pyproject.toml) using a `dev` dependency group.
The `dev` group includes all development dependencies:
- Development tools (ruff, pre-commit, invoke, etc.)
- Testing dependencies (pytest, mock, etc.)
- Documentation dependencies (mkdocs, etc.)
- Reporting dependencies (coverage, flake8, etc.)

To install the project with all development dependencies:

With [uv](https://docs.astral.sh/uv/) (recommended):
```shell
$ uv sync
```

The `dev` group is included by default. You can also be explicit:
```shell
$ uv sync --group dev
```

With pip (requires pip 25.1+):
```shell
$ pip install --group dev -e .
```

Note: `dependency-groups` are defined in [PEP 735](https://peps.python.org/pep-0735/). Both uv and pip (25.1+) support them.

If you need to add or modify a dependency, edit the [`pyproject.toml`](https://github.com/opendatateam/udata/blob/main/pyproject.toml) file directly in the appropriate section.


### Optimizing performances with Cython

Some dependencies have an optional compilation support for Cython
resulting in better performances (mostly XML harvesting).
To enable it, you need to install Cython before all other dependencies:

```shell
$ uv add Cython
$ uv sync
```

### macOS caveats

#### Package installation fails

If installing `Pillow` fails:

```shell
brew install libjpeg
uv sync
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
(you might want to have each one running in a terminal):

```shell
$ inv serve         # Start the development server

$ inv work          # Start a worker process
$ inv beat          # Start a scheduler process
```

## Common tasks

Most of the common tasks are scripted in the `tasks.py` file (which is using [invoke][]).
You can get the documentation related to all tasks with:

```shell
$ inv -l
```

It might be required to update your Python dependencies to ensure compatibility.
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
You may want to be able to [run the tests](testing-code.md) for a backend contribution,
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
