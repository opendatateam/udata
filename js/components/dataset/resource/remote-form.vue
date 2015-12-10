<template>
<form-horizontal class="resource-form remote-resource-form"
        :fields="fields" :model="resource" v-ref:form>
</form-horizontal>
</template>

<script>
export default {
    props: {
        resource: {
            type: Object,
            default() {return new Resource()}
        },
    },
    data: function() {
        return {
            fields: [{
                    id: 'title',
                    label: this._('Title')
                }, {
                    id: 'description',
                    label: this._('Description'),
                }, {
                    id: 'url',
                    label: this._('URL'),
                    widget: 'url-field',
                }, {
                    id: 'filesize',
                    label: this._('Size'),
                }, {
                    id: 'format',
                    label: this._('Format'),
                    widget: 'format-completer'
                }, {
                    id: 'mime',
                    label: this._('Mime Type'),
                }, {
                    id: 'checksum',
                    label: this._('Checksum'),
                    widget: 'checksum'
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
            return this.$refs.form.validate();
        },
        serialize: function() {
            return this.$refs.form.serialize();
        }
    }
};
</script>
