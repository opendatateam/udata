<template>
<div>
<job-widget :job="job" :loading="loading" :empty="empty">
    <div class="text-center">
        <button class="btn btn-primary btn-flat" @click="preview">
            <span class="fa fa-cog"></span>
            {{ _('Preview') }}
        </button>
    </div>
</job-widget>
</div>
</template>

<script>
import API from 'api';
import backends from 'models/harvest/backends';
import HarvestJob from 'models/harvest/job';
import HarvestSource from 'models/harvest/source';
import JobWidget from 'components/harvest/job.vue';

export default {
    name: 'HarvestPreviewView',
    components: {JobWidget},
    props: {
        source: {
            type: Object,
            default() {
                return new HarvestSource();
            }
        }
    },
    data() {
        return {
            job: new HarvestJob(),
            loading: false
        };
    },
    computed: {
        empty() {
            return this.job.created ? this._('No item found') : ' ';
        }
    },
    methods: {
        preview() {
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
