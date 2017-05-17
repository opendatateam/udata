<template>
<div>
<vertical-form v-ref:form :fields="fields" :model="post"></vertical-form>
</div>
</template>

<script>
import Post from 'models/post';
import VerticalForm from 'components/form/vertical-form.vue';

export default {
    name: 'post-form',
    components: {VerticalForm},
    props: {
        post: {type: Post, default: () => new Post()}
    },
    data() {
        return {
            fields: [{
                    id: 'name',
                    label: this._('Name')
                }, {
                    id: 'headline',
                    label: this._('Headline')
                }, {
                    id: 'content',
                    label: this._('Content')
                }, {
                    id: 'tags',
                    label: this._('Tags'),
                    widget: 'tag-completer'
                }, {
                    id: 'private',
                    label: this._('Draft')
                }]
        };
    },
    methods: {
        serialize() {
            return this.$refs.form.serialize();
        },
        validate() {
            return this.$refs.form.validate();
        }
    }
};
</script>
