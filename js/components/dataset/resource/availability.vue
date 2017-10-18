<template>
    <span v-if="availability === 'AVAILABLE'" class="badge bg-green">✓</span>
    <span v-if="availability === 'NOT_AVAILABLE'" class="badge bg-red">×</span>
    <span v-if="availability === 'UNKNOWN'" class="badge bg-gray">?</span>
</template>

<script>
export default {
    name: 'resource-availability',
    props: {
        resource: {
            type: Object,
            required: true,
        }
    },
    computed: {
        availability() {
            switch (this.resource.extras && this.resource.extras['check:available']) {
                case true:
                    return 'AVAILABLE';
                case false:
                    return 'NOT_AVAILABLE';
                default:
                    return 'UNKNOWN';
            }
        }
    }
}
</script>
