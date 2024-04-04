# Extending udata

udata is customizable in many ways, just choose yours.

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
- some hooks implementation

#### Hooks

Hooks are small html snippets loaded dynamicaly.

In any template, you can add a placeholder for hooks using one of these syntaxes:

```html+jinja
# All snippets concatened
{{ hook('my-custom-hook') }}

# More complex layout with a for loop
<ul>
{% for widget in hook('my-widgets') %}
<li>{{ widget }}</li>
{% endofr %}
</ul>

# Optionnal parameters support
{{ hook('my-parametric-hook', arg1, arg2, kw=value) }}
```

In a view plugin, a hook implementation is a simple decorated function with the context as first argument.

```python
from udata.frontend import template_hook

@template_hook
def my_hook(ctx):  # Will be available in {{ hook('my_hook') }}
    return 'my hook'


@template_hook('another-hook')  # Will be available as {{ hook('another-hook') }}
def my_custom_hook(ctx):
    return 'my custom hook'
```

A hook can render a template as simplfy as any basic view:

```python
@template_hook
def my_widget(ctx):
    return theme.render_template('my/widget.html, **ctx)
```

Hooks can be conditionnaly rendered:

```python
@template_hook('conditionnal-hook', when=lambda ctx: 'key' in ctx)
def my_conditionnal_hook(ctx):
    return 'key is present in context and value is {}'.format(ctx['key'])
```

Hooks can also receive parameters in addition to context:

```html+jinja
{{ hook('with-params', arg1, key=value) }}
```
```python
@template_hook('with-params')
def my_hook(ctx, arg, **kwargs):
    # Do something with params
```

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

### Previews (`udata.preview`)

A class entrypoint for preview providers.

These plugins should extend `udata.core.dataset.preview.PreviewPlugin`.

*Example:*

```python
from udata.core.dataset.preview import PreviewPlugin

class MyPreview(PreviewPlugin):
    def can_preview(self, resource):
        # Check whether or not you can display a preview
        # You can access the resource or its dataset (through resource.dataset)
        # to check your requirements

    def preview_url(self, resource):
        # Return the absolute preview URL for the given resource.
        # You can access the resource or its dataset (through resource.dataset)
        # to build your preview URL
```

You can mark a preview plugin as `fallback`, meaning it will only be a candidate
if other plugins can't provide a preview.
This is typically for plugin displaying generic preview (ie. only relying on mimetype for example):

```python
from udata.core.dataset.preview import PreviewPlugin

class MyGenericPreview(PreviewPlugin):
    fallback = True
```

Enabled plugins are cached so don't forget to [flush cache](administrative-tasks.md#cache) when:

- you change your `PLUGINS` configuration
- you deliver new plugin versions


### Generic plugins (`udata.plugins`)

A module entrypoint for generic plugins. They just have to expose a `init_app(app)` function
and can perform any manual initialization.

Use this entrypoint if you want to perform something not handled by previous entrypoints.

### Default settings

Any registered plugin may also expose some default settings in a `settings` module (ie. `my_plugin.settings`). They will be automatically discovered and registered.

### Translations

Any registered plugin may also expose translations in its root module `translations` directory.
They will be automatically discovered and loaded if the plugin is enabled.
Take a look at [adding-translations](adding-translations.md) to set up translations.

## Contributing

Last but not least, if none of the above match your needs,
you can also contribute to the core udata project and submit some contributions.

See [the Contributing Guide](contributing-guide)
