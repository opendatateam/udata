<template>
    <div :title="_('Click to trigger a new check')" v-if="!checking" @click.stop="refresh()">
        <span v-if="availability === 'AVAILABLE'" class="badge bg-green">✓</span>
        <span v-if="availability === 'NOT_AVAILABLE'" class="badge bg-red">×</span>
        <span v-if="availability === 'UNKNOWN'" class="badge bg-gray">?</span>
    </div>
    <div v-if="checking">
        <span class="badge bg-blue">↻</span>
    </div>
</template>

<script>
import API from 'api';

export default {
    name: 'resource-availability',
    props: {
        resource: {
            type: Object,
            required: true,
        },
        dataset: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            checking: false,
            availability: null,
        }
    },
    created() {
        this.availability = this.computeAvailability(this.resource.extras && this.resource.extras['check:available']);
    },
    methods: {
        computeAvailability(checkAvailable) {
            switch (checkAvailable) {
                case true:
                    return 'AVAILABLE';
                case false:
                    return 'NOT_AVAILABLE';
                default:
                    return 'UNKNOWN';
            }
        },
        refresh() {
            this.checking = true;
            API.datasets.check_dataset_resource({dataset: this.dataset.id, rid: this.resource.id, no_cache: true}, res => {
                this.availability = this.computeAvailability(res.obj['check:available']);
                this.checking = false;
            }, err => {
                console.log('Something went wrong with the check', err);
                this.availability = 'UNKNOWN';
                this.checking = false;
            });
        }
    }
}
</script>
