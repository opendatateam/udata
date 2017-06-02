# Running the project

Adapt the `Procfile.sample` file at the root of your repository by copying it to `Procfile` and uncommenting appropriated lines.

!!! note
    Or use the `--procfile` option which allows you to specify a path to a custom `Procfile` from wherever you want.

Then run all dependencies with:

```shell
$ honcho start
```

Now open your browser to [http://localhost:7000/][dev-server]. Everything is up and running!

!!! error
    If not, it's time for your first contribution to improve the documentation!
    But first let's try to figure out together what went wrong on [Gitter][].

You need to initialize some data before pushing uData to it's full potential:

```shell
# Initialize database, indexes...
$ udata init
# Optionnaly fetch and load some licenses
$ udata licenses https://www.data.gouv.fr/api/1/datasets/licenses
# Fetch last translations
$ tx pull
# Compile translations
$ inv i18nc
```

That's it! Now check out our advanced documentation for more customization.

[dev-server]: http://localhost:7000/
[gitter]: https://gitter.im/opendatateam/udata
