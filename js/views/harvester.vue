<template>
    <div class="row">
        <source-widget source="{{source}}" class="col-md-6"></source-widget>
        <jobs-widget jobs="{{jobs}}" current="{{current_job}}" class="col-md-6"></jobs-widget>
        <job-widget v-if="current_job" job="{{current_job}}" class="col-xs-12"></job-widget>
        <job-items-widget
            v-if="current_job"
            job="{{current_job}}"
            v-class="
                col-xs-12: !current_item,
                col-md-6: current_item,
            ">
        </job-items-widget>
        <job-item-widget v-if="current_item" item="{{current_item}}" class="col-md-6"></job-item-widget>
    </div>
    <div class="row"></div>
</template>

<script>
import HarvestJobs from 'models/harvest/jobs';
import HarvestSource from 'models/harvest/source';

export default {
    name: 'HarvestSourceView',
    data: function() {
        return {
            source_id: null,
            source: new HarvestSource(),
            jobs: new HarvestJobs({query: {page_size: 10}}),
            current_job: null,
            current_item: null,
            meta: {
                title: null,
                subtitle: null
            }
        };
    },
    events: {
        'harvest:job:selected': function(job) {
            this.current_job = job;
        },
        'harvest:job:item:selected': function(item) {
            this.current_item = item;
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
        'source-widget': require('components/harvest/source.vue'),
        'jobs-widget': require('components/harvest/jobs.vue'),
        'job-widget': require('components/harvest/job.vue'),
        'job-items-widget': require('components/harvest/job-items.vue'),
        'job-item-widget': require('components/harvest/job-item.vue'),
    }
};
</script>
