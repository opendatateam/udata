# Local dependencies

## Python and virtual environment

It is recommended to work within a virtualenv to ensure proper dependencies isolation.
If you're not familiar with that concept, read [Python Virtual Environments - a Primer][].

Alright, now you can [install virtualenv][install-virtualenv] and then type these commands knowing what you are doing:

```shell
$ virtualenv --python=python2.7 venv
$ source venv/bin/activate
$ pip install -r udata/requirements/develop.pip
$ pip install --no-deps -e udata/
```


## NodeJS and modules

You need NodeJS 4.2. If it's not already installed or you have a different version,
you should consider [installing NVM][nvm-install]. Then install JavaScript dependencies:

```shell
$ npm install
```

Once it's done, you should be able to run the build command for JS and CSS:

```shell
$ inv assets_build
```

!!! note
    If you plan to hack on statics (JS, CSS files), a dedicated command `inv assets_watch` will watch these files and recompile (the modified part only!) on each save.

[install-virtualenv]: https://virtualenv.pypa.io/en/latest/installation.html
[nvm-install]: https://github.com/creationix/nvm#installation
[Python Virtual Environments - a Primer]: https://realpython.com/blog/python/python-virtual-environments-a-primer/
