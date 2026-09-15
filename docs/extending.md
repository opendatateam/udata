# Extending udata

udata is customizable in many ways, just choose yours.

## Configuration

Before trying to code something specific, take a look at [all the settings](adapting-settings.md),
there may already be some details you can easily customize with a simple setting.

## Entrypoints

Entrypoints are modules or classes loaded by udata to extends its features.

An entrypoint is loaded as soon as the package declaring it is installed in the same
environment as udata. There is nothing to enable in the configuration.

### I18N (`udata.i18n`)

Plugins can expose a translation directory with the `udata.i18n` entrypoint. The module it
points at is used as the translation directory, and the entrypoint name as the domain — see
[adding-translations](adding-translations.md) to set them up.

### Harvesters (`udata.harvesters`)

Plugins can expose extra harvesters via the `udata.harvesters` class entrypoint.

See [the Harvesting section](harvesting.md#custom) for more details

### Tasks and jobs (`udata.tasks`)

This module entrypoint allows to register new asynchronous tasks and schedulable jobs.

### Generic plugins (`udata.plugins`)

A module entrypoint for generic plugins. They just have to expose a `init_app(app)` function
and can perform any manual initialization.

Use this entrypoint if you want to perform something not handled by previous entrypoints.

## Contributing

Last but not least, if none of the above match your needs,
you can also contribute to the core udata project and submit some contributions.

See [the Contributing Guide](contributing-guide.md).
