<template>
<job-widget :job="job" :loading="loading" :empty="empty">
    <div class="text-center">
        <button class="btn btn-primary btn-flat" @click="preview">
            <span class="fa fa-cog"></span>
            {{ _('Preview') }}
        </button>
    </div>
</job-widget>
</template>

<script>
import API from 'api';
import backends from 'models/harvest/backends';
import HarvestJob from 'models/harvest/job';
import HarvestSource from 'models/harvest/source';

export default {
    name: 'HarvestPreviewView',
    props: {
        source: {
            type: Object,
            default: function() {
                return new HarvestSource();
            }
        }
    },
    data: function() {
        return {
            job: new HarvestJob(),
            loading: false
        };
    },
    components: {
        'job-widget': require('components/harvest/job.vue')
    },
    computed: {
        empty: function() {
            return this.job.created ? this._('No item found') : ' ';
        }
    },
    methods: {
        preview: function() {
            this.loading = true;
            // this.$set('preview_job', job);
            API.harvest.preview_harvest_source(
                {ident: this.source.id},
                (response) => {
                    this.job.on_fetched(response);
                    this.loading = false;
                }
            );
        }
    }
};
</script>
