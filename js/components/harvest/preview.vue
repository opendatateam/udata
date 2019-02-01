<template>
<div>
<job-widget :job="job" :loading="loading" :empty="empty" with-slot>
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
        },
        fromConfig: {
            type: Boolean,
            default: false,
        },
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
            if (this.fromConfig) {
                API.harvest.preview_harvest_source_config(
                    {payload: this.source},
                    this.onPreviewFetch,
                    this.$root.handleApiError
                );
            } else {
                API.harvest.preview_harvest_source(
                    {ident: this.source.id},
                    this.onPreviewFetch,
                    this.$root.handleApiError
                );
            }
        },
        onPreviewFetch(response) {
            this.job.on_fetched(response);
            this.loading = false;
        }
    }
};
</script>
