# udata setup instructions

This guide is about starting a udata and udata-front environment for local development.

We’ll use the following repositories:

- [https://github.com/opendatateam/udata](https://github.com/opendatateam/udata)
- [https://github.com/datagouv/udata-front](https://github.com/datagouv/udata-front)

# Check the system requirements

!!! info
    Be aware that udata now requires Python **>3.11,<=3.13** to work.

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
│   ├── setup.py
│	└── udata.cfg
└── udata-front
    ├── ...
    └── setup.py
```

## Get udata

Make a new directory. You can name it as you like :

```shell
mkdir udata-workspace
cd udata-workspace
export UDATA_WORKSPACE=`pwd`  # we'll use UDATA_WORKSPACE env in the instructions
```

In this new directory, clone udata :

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

With pip (requires pip 25.1+):
```shell
python3 -m venv .venv
source .venv/bin/activate
pip install --group dev -e .
```

You can find [common errors and workarounds for Macos on udata documentation](https://udata.readthedocs.io/en/latest/development-environment/#macos-big-sur-caveat).

!!! info
    You need to make sure that your virtualenv is activated for the entire development process.

## Configure udata

udata uses a config file called `udata.cfg` and a custom directory as base for its filesystem, we’ll call it `fs`. You can put them as shown below.

```shell
$UDATA_WORKSPACE
├── fs
└── udata
    ├── ...
    ├── setup.py
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

This define `dev.local:7000` as the URL for your local setup. You’ll have to edit your `/etc/hosts` (Linux) or `C:\Windows\System32\drivers\etc\hosts` (Windows) to add this rule.

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

Now, you can use your udata api !

```shell
curl http://dev.local:7000/api/1/datasets/
```

You can see API endpoints by going to [http://dev.local:7000/api/1/](http://dev.local:7000/api/1/) in
your browser.

Workers are required for tasks to execute (search indexation, etc.).
```shell
source $UDATA_WORKSPACE/udata/venv/bin/activate  # Make sure your virtualenv is activated
inv work
```

!!! info
    You now have a working udata instance but no frontend for the platform.

# Install udata-front

With a valid udata environment, you can start the udata-front installation:

```shell
$UDATA_WORKSPACE
├── fs
├── udata
│   ├── ...
│   ├── setup.py
│	└── udata.cfg
└── udata-front
    ├── ...
    └── setup.py
```

First, clone udata-front in your workspace.

```shell
cd $UDATA_WORKSPACE
git clone git@github.com:datagouv/udata-front.git
```

Modify your `udata.cfg` with the following lines.

```shell
THEME = 'gouvfr'
```

udata-front uses the same virtualenv as udata. You can activate it from your udata-front directory if it’s not the case anymore.

```shell
source $UDATA_WORKSPACE/udata/venv/bin/activate
```

Then, you can install the requirements with:
```shell
cd udata-front
uv sync
```

...or, with pip:
```shell
cd udata-front
pip install -e ".[dev]"
```

The last thing to do is to install udata-front NPM packages.

!!! info
    udata and udata-front use different node versions so don’t forget to run `nvm use` when you switch from one to the other.

```shell
nvm install
nvm use

npm install
```

Once it's done, you should be able to run the build commands for JS and CSS.

```shell
inv assets-build
```

## Start udata with udata-front

To start udata, the inv command is the same.

```shell
cd $UDATA_WORKSPACE/udata
inv serve
```

You can now visit `dev.local:7000/` in your browser and start playing with your udata instance.

You can use parcel to watch for file changes in udata or udata-front directory with

```shell
inv assets-watch
```

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

[github]: https://github.com/opendatateam/udata
[new issue]: https://github.com/opendatateam/udata/issues/new
[udata-search-service]: https://github.com/opendatateam/udata-search-service
[udata-fixtures]: https://github.com/opendatateam/udata-fixtures
