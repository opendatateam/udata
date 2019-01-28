<template>
<div>
  <vertical-form v-ref:form :fields="fields" :model="reuse"></vertical-form>
</div>
</template>

<script>
import Reuse from 'models/reuse';
import reuse_types from 'models/reuse_types';
import VerticalForm from 'components/form/vertical-form.vue';

export default {
    components: {VerticalForm},
    props: {
        reuse: {
            type: Object,
            default: function() {
                return new Reuse();
            }
        },
    },
    data() {
        return {
            fields: [{
                    id: 'title',
                    label: this._('Name')
                }, {
                    id: 'url',
                    label: this._('URL'),
                    widget: 'url-field',
                }, {
                    id: 'type',
                    label: this._('Type'),
                    widget: 'select-input',
                    values: reuse_types,
                    map(item) {
                        return {value: item.id, text: item.label};
                    }
                }, {
                    id: 'description',
                    label: this._('Description'),
                }, {
                    id: 'tags',
                    label: this._('Tags'),
                    widget: 'tag-completer'
                }, {
                    id: 'private',
                    label: this._('Private')
                }]
        };
    },
    methods: {
        serialize() {
            return this.$refs.form.serialize();
        },
        validate() {
            return this.$refs.form.validate();
        },
        on_error(response) {
            return this.$refs.form.on_error(response);
        },
    }
};
</script>
