# Udata setup instructions

This guide is about starting a udata and udata-front environment for local development.

We’ll use the following repositories:

[https://github.com/opendatateam/udata](https://github.com/opendatateam/udata)

[https://github.com/etalab/udata-front](https://github.com/etalab/udata-front)

# Check the system requirements

Udata requires several libraries to be installed to work. You can see them on the udata documentation link below.

Be aware that udata now requires Python **>3.7** to work. 

We’ll use [docker-compose](https://docs.docker.com/compose/) to manage external services so you don’t have to install native mongodb, elasticsearch and redis.

[System dependencies - uData Documentation](https://udata.readthedocs.io/en/latest/system-dependencies/)

<aside>
⚠️ On ARM architecture such as Mac M1, you’ll have to use a native elasticsearch because there is no docker image available. You can download it from the [official website](https://www.elastic.co/fr/downloads/past-releases/elasticsearch-2-4-6).

You’ll have to launch the binary `./bin/elasticsearch` in addition to the docker-compose command.

</aside>

# Setup Udata

Udata requires a directory to contain the project, its plugins and all associated content, like the following schema. We’ll make all this together.

```bash
$WORKSPACE
├── fs
├── udata
│   ├── ...
│   └── setup.py
│		└── udata.cfg
└── udata-front
    ├── ...
    └── setup.py
```

## Get udata

Make a new directory. You can name it as you like :

```bash
mkdir udata-workspace
```

In this new directory, clone Udata :

```bash
cd udata-workspace
git clone git@github.com:opendatateam/udata.git
```

You can start your local development environment with docker-compose.

```bash
cd udata
docker-compose up
```

In a new shell, you can then try to interact with your local elasticsearch with the following query. It should output a JSON search response.

```bash
curl http://localhost:9200
```

## Install virtual env and dependencies

Udata uses pip to install its dependencies. You can create a [virtualenv](https://realpython.com/blog/python/python-virtual-environments-a-primer/), activate it and install the requirements with the following commands.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements/develop.pip
pip install -e .
```

You can find [common errors and workarounds for Macos on udata documentation](https://udata.readthedocs.io/en/latest/development-environment/#macos-big-sur-caveat).

You need to make sure that your virtualenv is activated for the entire development process.

## Install nvm and dependencies

Udata and udata-front use NVM to manage node versions (based on `.nvmrc` file). You can install it based on [their instructions](https://github.com/nvm-sh/nvm).

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

Udata uses a config file called `udata.cfg` and a custom directory as base for its filesystem, we’ll call it `fs`. You can put them as shown below.

```bash
$WORKSPACE
├── **fs**
└── udata
    ├── ...
    └── setup.py
 		└── **udata.cfg**
```

A sample content of `udata.cfg` is shown below.

```bash
from udata.settings import Defaults

DEBUG = True
SEND_MAIL = False
SERVER_NAME ='dev.local:7000'
CACHE_TYPE = 'null'

URLS_ALLOW_PRIVATE = True
URLS_ALLOW_LOCAL = True
URLS_ALLOWED_TLDS = Defaults.URLS_ALLOWED_TLDS | set(['local'])

RESOURCES_FILE_ALLOWED_DOMAINS = ['*']
PLUGINS = []
FS_ROOT = 'fs'

POST_DISCUSSIONS_ENABLED = True
```

This define `dev.local:7000` as the URL for your local setup. You’ll have to edit your `/etc/hosts` to add this rule.

```bash
127.0.0.1       dev.local
```

## Running the project for the first time

You need to initialize some data before being able to use udata.

```bash
# Initialize database, indexes...
# You must reply "n" to "Do you want to import some spatial zones (countries)?"
# Fixtures generation will fail because they require udata-front
udata init

# Compile translations
inv i18nc
```

You can then start udata server with the `serve` subcommand.

```bash
inv serve
```

Now, you can use your udata api !

```bash
curl http://dev.local:7000/api/1/datasets/
```

Workers are required for search reindex.

```bash
inv work
```

# Install Udata-front

With a valid udata environment, you can start the udata-front installation.

```bash
$WORKSPACE
├── **fs**
├── udata
│   ├── ...
│   └── setup.py
│		└── **udata.cfg**
└── udata-front
    ├── ...
    └── setup.py
```

First, clone udata-front in your workspace.

```bash
git clone git@github.com:etalab/udata-front.git
```

Modify your `udata.cfg` with the following lines.

```bash
PLUGINS = ['front']
THEME = 'gouvfr'
```

Udata-front uses the same virtualenv as udata. You can activate it from your udata-front directory if it’s not the case anymore.

```bash
source ../udata/venv/bin/activate
```

Then, you can install pip requirements.

```bash
cd udata-front
pip install -e . -r requirements/test.pip -r requirements/develop.pip
```

The last thing to do is to install udata-front NPM packages.

<aside>
ℹ️ udata and udata-front use different node versions so don’t forget to run `nvm use` when you switch from one to the other.

</aside>

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
inv serve
```

You can now visit `dev.local:7000/` in your browser and start playing with your udata instance.

You can use parcel to watch for file changes in udata or udata-front directory with

```bash
inv assets-watch 
# npm start # this command does the same thing
```

# Other commands

If you didn’t do it in `udata init`, you can add some default licences to your environment. 

```bash
udata licenses
```

If you didn’t do it in `udata init`, you can also add some fixtures to your local setup.

```bash
udata generate-fixtures
```

If you don’t use workers, you can rebuild the search index with the following command.

```bash
udata search index
```
