<template>
<div class="fr-toggle fr-toggle--label-left">
    <input @click="toggleFeatured" type="checkbox" class="fr-toggle__input" id="featured-toggle" :checked="featured">
    <label class="fr-toggle__label" for="featured-toggle" :data-fr-checked-label="$t('Unfeature this content')" :data-fr-unchecked-label="$t('Feature this content')"></label>
</div>
</template>

<script>
import {defineComponent} from "vue";
export default defineComponent({
    name: "featured-button",
    props: {
        subjectId: String,
        subjectType: String,
        featured: Boolean,
    },
    mounted() {
        this._featured = this.featured;
    },
    methods: {
        toggleFeatured() {
            const method = this._featured ? 'delete' : 'post';
            const url = `${this.subjectType.toLowerCase()}s/${this.subjectId}/featured/`;
            this.$api[method](url)
                .then(response => {
                    this._featured = !this._featured;
                })
                .catch(() => this.$toast.error(this.$t('An error occurred while featuring this subject.')));

        }
    },
});
</script>
