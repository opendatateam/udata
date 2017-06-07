<template>
<vform v-ref:form :fields="fields" :model="source"></vform>
</template>

<script>
import HarvestSource from 'models/harvest/source';


export default {
    props: {
        source: {
            type: HarvestSource,
            default() {
                return new HarvestSource();
            }
        },
        hideNotifications: false
    },
    data() {
        return {
            fields: [{
                id: 'name',
                label: this._('Name')
            }, {
                id: 'backend',
                label: this._('Backend')
            }, {
                id: 'url',
                label: this._('URL'),
                widget: 'url-field',
            }, {
                id: 'description',
                label: this._('Description'),
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
        serialize() {
            return this.$refs.form.serialize();
        },
        validate() {
            const isValid = this.$refs.form.validate();

            if (isValid & !this.hideNotifications) {
                this.$dispatch('notify', {
                    autoclose: true,
                    title: this._('Changes saved'),
                    details: this._('Your source has been updated.')
                });
            }
            return isValid;
        }
    }
};
</script>
