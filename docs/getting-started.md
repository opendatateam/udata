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

You can find [common errors and workarounds for MacOS on udata documentation](https://udata.readthedocs.io/en/latest/development-environment/#macos-big-sur-caveat).

!!! info "About the `uv run` prefix"
    The rest of this guide prefixes every command with `uv run`, which runs it in the
    project virtualenv without activating it. If you installed with `pip`, activate the
    virtualenv once (`source .venv/bin/activate`) and drop the prefix: `udata init`,
    `inv serve`, etc.

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

# generate secrets with `python -c "import secrets; print(secrets.token_urlsafe(64))"`
SECRET_KEY='generated-secret'
API_TOKEN_SECRET='another-generated-secret'
ELASTICSEARCH_URL='http://localhost:9200'

HARVESTER_BACKENDS = ['dcat']
HARVEST_MAX_ITEMS = 100

DEBUG = True
SEND_MAIL = False
SERVER_NAME = 'dev.local:7000'
CDATA_BASE_URL = 'http://dev.local:3000'
CACHE_TYPE = 'flask_caching.backends.NullCache'

URLS_ALLOW_PRIVATE = True
URLS_ALLOW_LOCAL = True
URLS_ALLOWED_TLDS = Defaults.URLS_ALLOWED_TLDS | set(['local'])

FS_ROOT = 'fs'

SESSION_COOKIE_SECURE = False
```

This defines `dev.local:7000` as the URL for your local setup. You’ll have to edit your `/etc/hosts` (Linux) or `C:\Windows\System32\drivers\etc\hosts` (Windows) to add this rule.

```shell
127.0.0.1       dev.local
```

!!! warning "Use the same hostname for udata and cdata"
    Browser cookies ignore ports but not hostnames. If you serve udata on `dev.local:7000`
    and open cdata on `localhost:3000`, the session cookie set by udata is never sent back
    by the browser and you stay logged out, whatever the CORS settings. Both must use the
    same hostname: `dev.local:7000` and `dev.local:3000`.

!!! WARNING
    For MacOS users, please note that the [control center is listening on port 7000](https://discussions.apple.com/thread/250472145?sortBy=rank),
    so the above won't work. Instead, configure for example port `7001` in the `udata.cfg` file.

## Running the project for the first time

You need to initialize some data before being able to use udata. The following command
will initialize database, indexes, create fixtures, etc.

```shell
uv run udata init
```

!!! note "Fixtures loading"
    Loading fixtures is done under the hood using the `import-fixtures` command,
    which imports sample data (datasets, posts, pages, site) from the bundled
    fixture file.

You can then start udata server with the `serve` subcommand.

```shell
uv run inv serve
```

!!! WARNING
    For MacOS users, this won't work as the port `7000` is already used, as explained above. If you've changed the `udata.cfg` to
    have a `SERVER_NAME=dev.local:7001`, use the following command instead, and make sure to use the port `7001` throughout the rest
    of the documentation and examples.

    ```shell
    uv run inv serve --port 7001
    ```

Now, you can use your udata API!

```shell
curl http://dev.local:7000/api/1/datasets/
```

You can see API endpoints by going to [http://dev.local:7000/api/1/](http://dev.local:7000/api/1/) in
your browser.

Workers are required to execute asynchronous tasks (search indexation, etc.). Start one in
another terminal:

```shell
cd $UDATA_WORKSPACE/udata
uv run inv work
```

# Running udata without a frontend

You now have a working udata instance, without any frontend. This is enough for most
testing needs, since everything udata does is reachable from the API and the command line:

```shell
# Browse and exercise the API
curl http://dev.local:7000/api/1/datasets/

# Create an API token from an account you own, then use it as a bearer token
curl -H "Authorization: Bearer <token>" http://dev.local:7000/api/1/me/

# Create a harvester and run it synchronously, as many times as you need
uv run udata harvest create dcat https://example.org/catalog.rdf "My harvester"
uv run udata harvest sources
uv run udata harvest run <source-id>

# Inspect the database with the models loaded
uv run udata shell
```

!!! tip "Debugging a harvester"
    `udata harvest run` is synchronous: it needs no worker and prints everything to your
    terminal, which makes it the fastest way to replay a harvest against a remote catalog
    and read the errors.

!!! warning "Enable the backend first"
    No harvester backend is enabled by default. `harvest create` accepts any backend name,
    but `harvest run` then fails with `Backend dcat unknown. Make sure it is declared in
    HARVESTER_BACKENDS.` if it is not enabled. The sample `udata.cfg` above enables `dcat`;
    add the others you need (`HARVESTER_BACKENDS = ['dcat', 'csw*']`), see
    [harvesting](harvesting.md).

See [administrative tasks](administrative-tasks.md) for the other commands, [API tokens](api-tokens.md)
to authenticate your calls and [harvesting](harvesting.md) for the harvesters.

Install cdata below only if you need the web interface itself.

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

Then install its packages using [pnpm][].

!!! info
    cdata uses Node.js, so make sure you have the correct Node.js version installed. Don't forget to run `nvm use` when switching to the cdata directory.

```shell
cd cdata
nvm install
nvm use

pnpm install
```

## Start udata with cdata

udata and cdata are two separate servers: udata no longer renders any page, it only serves
the API that cdata calls. You need both running, each in its own terminal.

```shell
# Terminal 1: the udata API, on dev.local:7000
cd $UDATA_WORKSPACE/udata
uv run inv serve
```

```shell
# Terminal 2: the cdata frontend, on dev.local:3000
cd $UDATA_WORKSPACE/cdata
pnpm run build
pnpm run preview
```

By default cdata calls the API on `http://dev.local:7000`, which matches the `SERVER_NAME`
set above. `NUXT_PUBLIC_API_BASE` is read when the server starts, not baked at build time,
so you can point the same build at another instance:

```shell
NUXT_PUBLIC_API_BASE=http://dev.local:7001 pnpm run preview
```

!!! info "`preview` or `dev`?"
    `pnpm run build` + `pnpm run preview` serves the production build — this is what cdata's
    own end-to-end suite runs against, and what is deployed. Prefer it to run an instance:
    pages are served already compiled, and you avoid the file-watcher issues that come with
    the dev server. Use `pnpm run dev` when you are working on cdata itself and want hot
    reload, rebuilding after each change otherwise.

You can now visit [http://dev.local:3000/](http://dev.local:3000/) in your browser and start
playing with your instance.

!!! warning
    Open `dev.local:3000`, not `localhost:3000`. Both resolve to the same server, but the
    session cookie is set on the `dev.local` host: reaching cdata through `localhost` logs
    you out on every API call.

!!! note "Tell us what you think"
    You are always welcome to tell us about your experience _installing udata_.
    Get in touch with us by raising a [new issue][] on [GitHub][].

# Other commands

You can rebuild the search index with the following command.

```shell
uv run udata search index
```

Finally, you can see other administrative tasks in [administrative-tasks](administrative-tasks.md)

# Going further

Once the project is up and running, it's time to customize it! Take a look at our advanced documentation on [adapting settings](adapting-settings.md), [extending udata](extending.md), [testing your code](testing-code.md), [adding translation](adding-translations.md) and so on.

[cdata]: https://github.com/datagouv/cdata
[github]: https://github.com/opendatateam/udata
[new issue]: https://github.com/opendatateam/udata/issues/new
[pnpm]: https://pnpm.io/
[udata]: https://github.com/opendatateam/udata
