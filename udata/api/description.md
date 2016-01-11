## {{ _('Authentication') }}

{{ _('In order to be able to execute write operations,') }}
{{ _('you first need to obtain an [API Key] in your profile settings.') }}
{{ _('This key should be provided on each call in the `X-API-KEY` HTTP header.') }}

## {{ _('Authorizations') }}

{{ _('API calls are subject to the same permissions than the web interface.') }}

{{ _('By example, you need to be part of the organization to modify one of its datasets.') }}

## {{ _('Pagination') }}

{% trans %}
Some method are paginated and always follow the same pattern.
The object list is wrapped in a `Page` object.

You don't have to compute yourself the previous and next pages
because the URLs are available in the response under the
`previous_page` and `next_page` attributes.
They will be set to `null` if there is no previous and/or next page.
{% endtrans %}

### {{ _('Example') }}

```json
{
    "data": [{...}, {...}],
    "page": 1,
    "page_size": 20,
    "total": 43,
    "next_page": "http://{{config.SERVER_NAME}}/api/endpoint/?page=2",
    "previous_page": null
}
```

## {{ _('Masks') }}



[API Key]: {{url_for('admin.index', path='me/', _external=True)}}
