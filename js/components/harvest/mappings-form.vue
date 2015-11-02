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
        }
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
            return this.$refs.form.validate();
        },
        preview: function() {
            let job = new HarvestJob();
            this.$set('preview_job', job);
            API.harvest.preview_harvest_source(
                {ident: this.source.id},
                job.on_fetched.bind(job)
            );
        }
    }
};
</script>
