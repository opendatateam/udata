<template>
<form-vertical v-ref="form" fields="{{fields}}" model="{{source}}"></form-vertical>
<!--div class="row">
    <div class="col-xs-12 text-center" v-class="col-md-6: preview_job">
        <button class="btn btn-primary" v-on="click: preview">
            <span class="fa fa-cog"></span>
            {{ _('Preview') }}
        </button>
    </div>
    <job-widget v-if="preview_job"
        job="{{preview_job}}"
        class="col-xs-12 col-md-6">
    </job-widget>
</div-->
</template>

<script>
import API from 'api';
import backends from 'models/harvest/backends';
import HarvestJob from 'models/harvest/job';
import HarvestSource from 'models/harvest/source';

export default {
    name: 'HarvestMappingView',
    props: ['source'],
    data: function() {
        return {
            source: new HarvestSource(),
            fields: [],
            preview_job: null
        };
    },
    components: {
        'form-vertical': require('components/form/vertical-form.vue'),
        'job-widget': require('components/harvest/job.vue')
    },
    methods: {
        serialize: function() {
            return this.$.form.serialize();
        },
        validate: function() {
            return this.$.form.validate();
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
