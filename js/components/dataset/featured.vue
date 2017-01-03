<template>
<div class="btn-group btn-group-sm">
    <button type="button"
        class="btn btn-success featured"
        :class="{active: featured}"
        @click="toggleFeatured">
        <span class="fa fa-bullhorn"></span>
        {{ _('Featured') }}
    </button>
</div>
</template>

<script>
import Auth from 'auth';
import log from 'logger';

export default {
    props: {
        datasetId: String,
        featured: false,
        required: true
    },
    methods: {
        toggleFeatured() {
            Auth.need_role('admin');
            const method = this.featured ? 'delete' : 'post';
            this.$api[method](`datasets/${this.datasetId}/featured/`)
                .then(response => {
                    this.featured = !this.featured;
                })
                .catch(log.error.bind(log));

        }
    },
}
</script>
