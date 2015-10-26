<template>
<form-horizontal class="resource-form api-resource-form"
        fields="{{fields}}" model="{{resource}}" v-ref="form">
</form-horizontal>
</template>

<script>
export default {
    inherit: true,
    data: function() {
        return {
            fields: [{
                    id: 'title',
                    label: this._('Title'),
                    help: this._('The title of the API. The first thing the user will see.')
                }, {
                    id: 'url',
                    label: this._('URL'),
                    help: this._('The public URL of the API')
                }, {
                    id: 'description',
                    label: this._('Description'),
                    help: this._('Some details about the API.')
                }, {
                    id: 'published',
                    label: this._('Publication date'),
                    widget: 'date-picker'
                }]
        };
    },
    components: {
        'form-horizontal': require('components/form/horizontal-form.vue')
    },
    methods: {
        validate: function() {
            return this.$.form.validate();
        },
        serialize: function() {
            return this.$.form.serialize();
        }
    }
};
</script>
