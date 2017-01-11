<template>
<button type="button" class="btn featured"
    :class="{active: featured, 'btn-success': !compact, 'btn-default': compact}"
    @click="toggleFeatured"
    v-tooltip="_('Feature this content')" tooltip-placement="tooltipPlacement">
    <span class="fa fa-bullhorn"></span>
    <span v-if="!compact">{{ _('Featured') }}</span>
</button>
</template>

<script>
import Auth from 'auth';
import log from 'logger';

export default {
    props: {
        subjectId: String,
        subjectType: String,
        featured: Boolean,
        compact: Boolean
    },
    methods: {
        toggleFeatured() {
            Auth.need_role('admin');
            const method = this.featured ? 'delete' : 'post';
            const url = `${this.subjectType.toLowerCase()}s/${this.subjectId}/featured/`;
            this.$api[method](url)
                .then(response => {
                    this.featured = !this.featured;
                })
                .catch(log.error.bind(log));

        }
    },
}
</script>
