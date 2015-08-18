<template>
<form-vertical v-ref="form" fields="{{fields}}" model="{{source}}"></form-vertical>
<div class="row">
    <div class="clox-xs-12 text-center">
        <button class="btn btn-primary" v-on="click: preview">
            <span class="fa fa-cog"></span>
            {{ _('Preview') }}
        </button>
    </div>
</div>
<div class="row" v-if="preview_job">
    <job-widget
        job="{{preview_job}}"
        class="col-xs-12">
    </job-widget>
</div>
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
            API.harvest.preview_harvest_source(
                {ident: this.source.id},
                (response) => {
                    this.$set('preview_job', new HarvestJob({data: response.obj}));
                }
            );
        }
    }
};
</script>
