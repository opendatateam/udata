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

### MacOS caveats

#### Package installation fails

If installing `Pillow` fails:

```shell
brew install libjpeg
uv sync
```

#### Local web server is slow

If you're using `{something}.local` as your `SERVER_NAME`, you need to add an ipv6 resolution to this FQDN:

```
127.0.0.1   dev.local
::1         dev.local
```

[Reference and context here](https://superuser.com/a/1596341).

## Running the project

You can use [invoke][] to launch the application services
(you might want to have each one running in a terminal):

```shell
$ uv run inv serve         # Start the development server

$ uv run inv work          # Start a worker process
$ uv run inv beat          # Start a scheduler process
```

## Common tasks

Most of the common tasks are scripted in the `tasks/` package (which is using [invoke][]).
You can get the documentation related to all tasks with:

```shell
$ uv run inv -l
```

After pulling upstream changes or switching branch, resync your environment:

```shell
# Install the exact dependencies of the current lock file
$ uv sync

# Apply the pending database migrations
$ uv run udata db migrate

# Recompile the translations
$ uv run inv i18nc
```

Now check out our advanced documentation for a focus on some specific tasks.
You may want to be able to [run the tests](testing-code.md) for a backend contribution,
simply provide some fixes to [the translations](adding-translations.md)
or [the documentation](building-documentation.md).


[invoke]: http://www.pyinvoke.org/
