<template>
<div>
<horizontal-form class="resource-form remote-resource-form"
        :fields="fields" :model="resource" v-ref:form>
</horizontal-form>
</div>
</template>

<script>
import HorizontalForm from 'components/form/horizontal-form.vue';

export default {
    components: {HorizontalForm},
    props: {
        resource: {
            type: Object,
            default() {return new Resource()}
        },
    },
    data() {
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
    methods: {
        validate() {
            return this.$refs.form.validate();
        },
        serialize() {
            return this.$refs.form.serialize();
        }
    }
};
</script>
