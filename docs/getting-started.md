# udata setup instructions

This guide is about starting a udata backend and [cdata][] (formerly udata-front) frontend environment for local development.

We’ll use the following repositories:

- [udata][] - The backend API and core platform
- [cdata][] - The frontend repository

# Check the system requirements

!!! info
    Be aware that udata requires Python **>=3.11,<3.14** to work.

udata requires several libraries to be installed to work. You can see them on the udata documentation link below.

We’ll use [docker compose](https://docs.docker.com/compose/) to manage external services so you don’t have to install native mongodb and redis.

# Setup udata

udata requires a directory to contain the project, its plugins and all associated content.
The recommended layout for this directory is displayed in the following schema.
We’ll make all this together.

```shell
$UDATA_WORKSPACE
├── fs
├── udata
│   ├── ...
│   ├── pyproject.toml
│	└── udata.cfg
└── cdata
    └── ...
```

## Get udata

Make a new directory. You can name it as you like:

```shell
mkdir udata-workspace
cd udata-workspace
export UDATA_WORKSPACE=`pwd`  # we'll use UDATA_WORKSPACE env in the instructions
```

In this new directory, clone udata:

```shell
git clone git@github.com:opendatateam/udata.git
```

You can start your local development environment with docker compose.

```shell
cd udata
docker compose up
```

!!! warning
    If you have no output at all for too long, check the
    [IPv6 possible issue](https://github.com/docker/docker/issues/2174#issuecomment-35697655).

## Install virtual env and dependencies

With [uv](https://docs.astral.sh/uv/) (recommended):

```shell
uv sync
```

...or with pip (requires pip 25.1+):
```shell
python3 -m venv .venv
source .venv/bin/activate
pip install --group dev -e .
```

You can find [common errors and workarounds for macOS on udata documentation](https://udata.readthedocs.io/en/latest/development-environment/#macos-big-sur-caveat).

!!! info
    With `uv`, the virtual environment is managed automatically. With `pip`, you need to activate the virtualenv manually: `source .venv/bin/activate`.

## Configure udata

udata uses a config file called `udata.cfg` and a custom directory as a base for its filesystem, we’ll call it `fs`. You can put them as shown below.

```shell
$UDATA_WORKSPACE
├── fs
└── udata
    ├── ...
    ├── pyproject.toml
 	└── udata.cfg
```

A sample content of `udata.cfg` for local development is shown below.

```shell
from udata.settings import Defaults

DEBUG = True
SEND_MAIL = False
SERVER_NAME ='dev.local:7000'
CACHE_TYPE = 'flask_caching.backends.null'

URLS_ALLOW_PRIVATE = True
URLS_ALLOW_LOCAL = True
URLS_ALLOWED_TLDS = Defaults.URLS_ALLOWED_TLDS | set(['local'])

RESOURCES_FILE_ALLOWED_DOMAINS = ['*']
FS_ROOT = 'fs'

SESSION_COOKIE_SECURE = False
```

This defines `dev.local:7000` as the URL for your local setup. You’ll have to edit your `/etc/hosts` (Linux) or `C:\Windows\System32\drivers\etc\hosts` (Windows) to add this rule.

```shell
127.0.0.1       dev.local
```

!!! WARNING
    For MacOS users, please note that the [control center is listening on port 7000](https://discussions.apple.com/thread/250472145?sortBy=rank),
    so the above won't work. Instead, configure for example port `7001` in the `udata.cfg` file.

## Running the project for the first time

You need to initialize some data before being able to use udata. The following command
will initialize database, indexes, create fixtures, etc.

```shell
udata init
```

!!! note "Fixtures loading"
    Loading fixtures is done under the hood using the `import-fixtures` command,
    which relies on the [udata-fixtures][] repository, and will import the fixtures
    declared in the `FIXTURE_DATASET_SLUGS` config.

You can then start udata server with the `serve` subcommand.

```shell
inv serve
```

!!! WARNING
    For MacOS users, this won't work as the port `7000` is already used, as explained above. If you've changed the `udata.cfg` to
    have a `SERVER_NAME=dev.local:7001`, use the following command instead, and make sure to use the port `7001` throughout the rest
    of the documentation and examples.

    ```shell
    inv serve --port 7001
    ```

Now, you can use your udata API!

```shell
curl http://dev.local:7000/api/1/datasets/
```

You can see API endpoints by going to [http://dev.local:7000/api/1/](http://dev.local:7000/api/1/) in
your browser.

Workers are required to execute tasks (search indexation, etc.).

With `uv`:
```shell
cd $UDATA_WORKSPACE/udata
uv run inv work
```

With `pip` (if not already activated):
```shell
cd $UDATA_WORKSPACE/udata
source .venv/bin/activate
inv work
```

!!! info
    You now have a working udata instance but no frontend for the platform.

# Install cdata frontend (formerly udata-front)

With a valid udata environment, you can start the cdata installation:

```shell
$UDATA_WORKSPACE
├── fs
├── udata
│   ├── ...
│   ├── pyproject.toml
│	└── udata.cfg
└── cdata
    └── ...
```

First, clone cdata in your workspace.

```shell
cd $UDATA_WORKSPACE
git clone git@github.com:datagouv/cdata.git
```

Modify your `udata.cfg` with the following lines.

```shell
THEME = 'gouvfr'
```

The last thing to do is to install the frontend [cdata][] packages using [pnpm][].

!!! info
    cdata uses Node.js, so make sure you have the correct Node.js version installed. Don't forget to run `nvm use` when switching to the cdata directory.

```shell
cd cdata
nvm install
nvm use

pnpm install
```

Once it's done, you should be able to run the build commands for JavaScript and CSS in cdata.
Check the [cdata repository][cdata] documentation for the specific build commands.

## Start udata with cdata

To start udata, the inv command is the same.

```shell
cd $UDATA_WORKSPACE/udata
inv serve
```

You can now visit `dev.local:7000/` in your browser and start playing with your udata instance.

For watching and building frontend assets, check the [cdata repository][cdata] documentation for the specific commands.

!!! note "Tell us what you think"
    You are always welcome to tell us about your experience _installing udata_.
    Get in touch with us by raising a [new issue][] on [GitHub][].

# Other commands

You can rebuild the search index with the following command.

```shell
udata search index
```

Finally, you can see other administrative tasks in [administrative-tasks](administrative-tasks.md)

# Going further

Once the project is up and running, it’s time to customize it! Take a look at our advanced documentation on [adapting settings](adapting-settings.md), [extending udata](extending.md), [testing your code](testing-code.md), [adding translation](adding-translations.md), [setting up a search service][udata-search-service] and so on.

[cdata]: https://github.com/datagouv/cdata
[github]: https://github.com/opendatateam/udata
[new issue]: https://github.com/opendatateam/udata/issues/new
[pnpm]: https://pnpm.io/
[udata]: https://github.com/opendatateam/udata
[udata-search-service]: https://github.com/opendatateam/udata-search-service
[udata-fixtures]: https://github.com/opendatateam/udata-fixtures
