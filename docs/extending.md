# Extending uData

uData is customizable in many ways, just choose yours.

## Configuration

Before trying to code something specific, take a look at [all the settings](adapting-settings.md),
there may already be some details you can easily customize with a simple setting.

## Themes

You can totally customize the udata appearence with themes.

See the [dedicated section](creating-theme.md) for more details.

**NB**: A theme is also an [entrypoint](#entrypoints), but a special one.

## Entrypoints

Entrypoints are modules or classes loaded by udata to extends its features.

### Harvesters (`udata.harvesters`)

Plugins can expose extra harvesters via the `udata.harvesters` class entrypoint.

See [the Harvesting section](harvesting.md#custom) for more details

### Views (`udata.views`)

Plugins can expose extra view features via the `udata.views` module entrypoint including:

- a blueprint (should be named `blueprint`)
- some view filters

### Metrics (`udata.metrics`)

A module entrypoint allowing to register new metrics.

### Models (`udata.models`)

This module entrypoint allows you to expose new models or to extend existing ones by adding new badges or new known extras.

Models entrypoints may also expose migrations in the `migrations` folder sibling to the `models` module.
If you only need to expose migrations, just provide an empty `models` module.

### Link checkers (`udata.linkcheckers`)

This class entrypoint allows to register new link checkers that udata will recognize and use.

### Tasks and jobs (`udata.tasks`)

This module entrypoint allows to register new asynchronous tasks and schedulable jobs.

### Generic plugins (`udata.plugins`)

A module entrypoint for generic plugins. They just have to expose a `init_app(app)` function
and can perform any manual initialization.

Use this entrypoint if you want to perform something not handled by previous entrypoints.

### Translations

Any registered plugin may also expose translations in its root module `translations` directory.
They will be automatically discovered and loaded if the plugin is enabled.

## Contributing

Last but not least, if none of the above match your needs,
you can also contribute to the core udata project and submit some contributions.

See [the Contributing Guide](contributing-guide)
