# Building the documentation

So meta. First of, activate your virtualenv and install dedicated dependencies:

```shell
$ pip install -r requirements/doc.pip
```

Then you should be able to build and serve the documentation using the dedicated invoke task:

```shell
$ inv doc
```

Open [http://127.0.0.1:8000/][docs-server] and enjoy the live reload of your changes.
Docs are located within the `udata/docs/*` directory and use the markdown format.

Behind the scene, it uses [MkDocs][] so feel free to use directly for advanced usage:

```shell
$ mkdocs --help
```

[mkdocs]: http://www.mkdocs.org/
[docs-server]: http://127.0.0.1:8000/
