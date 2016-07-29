<template>
<vform v-ref:form :fields="fields" :model="post"></vform>
</template>

<script>
import Post from 'models/post';
import Vform from 'components/form/vertical-form.vue';

export default {
    props: {
        post: {
            type: Post,
            default() {
                return new Post();
            }
        }
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
    components: {Vform},
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
