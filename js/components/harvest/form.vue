<template>
<vform v-ref:form :fields="fields" :model="source"></vform>
</template>

<script>
import HarvestSource from 'models/harvest/source';
import backends from 'models/harvest/backends';

export default {
    name: 'HarvestSourceForm',
    props: {
        source: {
            type: HarvestSource,
            default() {
                return new HarvestSource();
            }
        },
        hideNotifications: false
    },
    data: function() {
        return {
            fields: [{
                    id: 'name',
                    label: this._('Name')
                }, {
                    id: 'description',
                    label: this._('Description')
                }, {
                    id: 'url',
                    label: this._('URL'),
                    widget: 'url-field',
                }, {
                    id: 'backend',
                    label: this._('Backend'),
                    widget: 'select-input',
                    values: backends.items.map(function(item) {
                        return {value: item.id, text: item.label};
                    })
                }, {
                    id: 'active',
                    label: this._('Active')
                }]
        };
    },
    components: {
        vform: require('components/form/vertical-form.vue')
    },
    methods: {
        serialize: function() {
            return this.$refs.form.serialize();
        },
        validate: function() {
            const isValid = this.$refs.form.validate();

            if (isValid & !this.hideNotifications) {
                this.$dispatch('notify', {
                    autoclose: true,
                    title: this._('Changes saved'),
                    details: this._('The harvester has been updated.')
                });
            }
            return isValid;
        }
    }
};
</script>
