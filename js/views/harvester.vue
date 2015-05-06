<template>
    <div class="row">
        <harvest-source-widget source="{{source}}" class="col-md-6"></harvest-source-widget>
        <harvest-jobs-widget jobs="{{jobs}}" current="{{current_job}}" class="col-md-6"></harvest-jobs-widget>
    </div>
    <div class="row"></div>
</template>

<script>
'use strict';

var HarvestJobs = require('models/harvest/jobs'),
    HarvestJob = require('models/harvest/job'),
    HarvestSource = require('models/harvest/source');

module.exports = {
    name: 'HarvestSourceView',
    data: function() {
        return {
            source_id: null,
            source: new HarvestSource(),
            jobs: new HarvestJobs({query: {page_size: 10}}),
            current_job: new HarvestJob(),
            meta: {
                title: null,
                subtitle: null
            }
        };
    },
    events: {
        'harvest:job:selected': function(job) {
            this.current_job = job;
        }
    },
    watch: {
        source_id: function(id) {
            if (id) {
                this.source.fetch(id);
            }
        },
        'source.id': function(id) {
            if (id) {
                this.jobs.fetch({ident: id});
            }
        },
        'source.name': function(name) {
            if (name) {
                this.meta.title = name;
                this.$dispatch('meta:updated', this.meta);
            }
        },
        'source.backend': function(backend) {
            if (backend) {
                this.meta.subtitle = backend;
                this.$dispatch('meta:updated', this.meta);
            }
        }
    },
    components: {
        'harvest-source-widget': require('components/harvest/source.vue'),
        'harvest-jobs-widget': require('components/harvest/jobs.vue')
    }
};
</script>
