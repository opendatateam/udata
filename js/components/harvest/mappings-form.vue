<template>
<vform v-ref:form :fields="fields" :model="source"></vform>
</template>

<script>
import API from 'api';
import backends from 'models/harvest/backends';
import HarvestJob from 'models/harvest/job';
import HarvestSource from 'models/harvest/source';

export default {
    name: 'HarvestMappingView',
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
            fields: [],
            preview_job: null
        };
    },
    components: {
        vform: require('components/form/vertical-form.vue'),
        'job-widget': require('components/harvest/job.vue')
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
                    details: this._('Your mapping has been updated.')
                });
            }
            return isValid;
        },
        preview: function() {
            let job = new HarvestJob();
            this.$set('preview_job', job);
            API.harvest.preview_harvest_source(
                {ident: this.source.id},
                job.on_fetched.bind(job),
                this.$root.handleApiError
            );
        }
    }
};
</script>
