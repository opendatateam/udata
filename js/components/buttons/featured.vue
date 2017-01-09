<template>
<button type="button"
    class="btn btn-success featured"
    :class="{active: featured}"
    @click="toggleFeatured">
    <span class="fa fa-bullhorn"></span>
    {{ _('Featured') }}
</button>
</template>

<script>
import Auth from 'auth';
import log from 'logger';

export default {
    props: {
        subjectId: String,
        subjectType: String,
        featured: false,
        btnClass: 'success'
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
