# udata setup instructions

This guide is about starting a udata and udata-front environment for local development.

We’ll use the following repositories:

- [https://github.com/opendatateam/udata](https://github.com/opendatateam/udata)
- [https://github.com/etalab/udata-front](https://github.com/etalab/udata-front)

# Check the system requirements

!!! info
    Be aware that udata now requires Python **>3.7,<3.10** to work. 

udata requires several libraries to be installed to work. You can see them on the udata documentation link below.

We’ll use [docker-compose](https://docs.docker.com/compose/) to manage external services so you don’t have to install native mongodb and redis.

# Setup udata

udata requires a directory to contain the project, its plugins and all associated content.
The recommended layout for this directory is displayed in the following schema.
We’ll make all this together.

```bash
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

```bash
mkdir udata-workspace
cd udata-workspace
export UDATA_WORKSPACE=`pwd`  # we'll use UDATA_WORKSPACE env in the instructions
```

In this new directory, clone udata :

```bash
git clone git@github.com:opendatateam/udata.git
```

You can start your local development environment with docker-compose.

```bash
cd udata
docker-compose up
```

!!! warning
    If you have no output at all for too long, check the
    [IPv6 possible issue](https://github.com/docker/docker/issues/2174#issuecomment-35697655).

## Install virtual env and dependencies

udata uses pip to install its dependencies. You can create a
[virtualenv](https://realpython.com/blog/python/python-virtual-environments-a-primer/),
activate it and install the requirements with the following commands.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements/develop.pip
pip install -e .
```

You can find [common errors and workarounds for Macos on udata documentation](https://udata.readthedocs.io/en/latest/development-environment/#macos-big-sur-caveat).

!!! info
    You need to make sure that your virtualenv is activated for the entire development process.

## Install nvm and dependencies

udata and udata-front use NVM to manage node versions (based on `.nvmrc` file). You can install it based on [their instructions](https://github.com/nvm-sh/nvm).

Then, you can install and activate the required node version.

```bash
nvm install
nvm use
```

You can install JavaScript dependencies with NPM.

```bash
npm install
```

Once it's done, you should be able to run the build commands for JS and CSS.

```bash
inv assets-build
inv widgets-build
```

## Configure udata

udata uses a config file called `udata.cfg` and a custom directory as base for its filesystem, we’ll call it `fs`. You can put them as shown below.

```bash
$UDATA_WORKSPACE
├── fs
└── udata
    ├── ...
    ├── setup.py
 	└── udata.cfg
```

A sample content of `udata.cfg` for local development is shown below.

```bash
from udata.settings import Defaults

DEBUG = True
SEND_MAIL = False
SERVER_NAME ='dev.local:7000'
CACHE_TYPE = 'flask_caching.backends.null'

URLS_ALLOW_PRIVATE = True
URLS_ALLOW_LOCAL = True
URLS_ALLOWED_TLDS = Defaults.URLS_ALLOWED_TLDS | set(['local'])

RESOURCES_FILE_ALLOWED_DOMAINS = ['*']
PLUGINS = []
FS_ROOT = 'fs'
```

This define `dev.local:7000` as the URL for your local setup. You’ll have to edit your `/etc/hosts` to add this rule.

```bash
127.0.0.1       dev.local
```

## Running the project for the first time

You need to initialize some data before being able to use udata. The following command
will initalize database, indexes, create fixtures, etc.

```bash
udata init
```

You can then start udata server with the `serve` subcommand.

```bash
inv serve
```

Now, you can use your udata api !

```bash
curl http://dev.local:7000/api/1/datasets/
```

You can see API endpoints by going to [http://dev.local:7000/api/1/](http://dev.local:7000/api/1/) in
your browser.

Workers are required for tasks to execute (search indexation, etc.).
```bash
source $UDATA_WORKSPACE/udata/venv/bin/activate  # Make sure your virtualenv is activated
inv work
```

!!! info
    You now have a working udata instance but no frontend for the platform.

# Install udata-front

With a valid udata environment, you can start the udata-front installation.

```bash
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

```bash
cd $UDATA_WORKSPACE
git clone git@github.com:etalab/udata-front.git
```

Modify your `udata.cfg` with the following lines.

```bash
PLUGINS = ['front']
THEME = 'gouvfr'
```

udata-front uses the same virtualenv as udata. You can activate it from your udata-front directory if it’s not the case anymore.

```bash
source $UDATA_WORKSPACE/udata/venv/bin/activate
```

Then, you can install pip requirements.

```bash
cd udata-front
pip install -e . -r requirements/test.pip -r requirements/develop.pip
```

The last thing to do is to install udata-front NPM packages.

!!! info
    udata and udata-front use different node versions so don’t forget to run `nvm use` when you switch from one to the other.

```bash
nvm install
nvm use

npm install
```

Once it's done, you should be able to run the build commands for JS and CSS.

```bash
inv assets-build
```

## Start udata with udata-front

To start udata, the inv command is the same.

```bash
cd $UDATA_WORKSPACE/udata
inv serve
```

You can now visit `dev.local:7000/` in your browser and start playing with your udata instance.

You can use parcel to watch for file changes in udata or udata-front directory with

```bash
inv assets-watch 
```

!!! note "Tell us what you think"
    You are always welcome to tell us about your experience _installing udata_.
    Get in touch with us by raising a [new issue][] on [GitHub][].

# Other commands

You can rebuild the search index with the following command.

```bash
udata search index
```

Finally, you can see other administrative tasks in [administrative-tasks](administrative-tasks.md)

# Going further

Once the project is up and running, it’s time to customize it! Take a look at our advanced documentation on [adapting settings](adapting-settings.md), [creating a custom theme](creating-theme.md), [extending udata](extending.md), [testing your code](testing-code.md), [adding translation](adding-translations.md), [setting up a search service][udata-search-service] and so on.

[github]: https://github.com/opendatateam/udata
[new issue]: https://github.com/opendatateam/udata/issues/new
[udata-search-service]: https://github.com/opendatateam/udata-search-service
