<template>
<vform v-ref:form :fields="fields" :model="post"></vform>
</template>

<script>
import Post from 'models/post';

export default {
    props: {
        post: {
            type: Post,
            default: function() {
                return new Post();
            }
        }
    },
    data: function() {
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
    components: {
        vform: require('components/form/vertical-form.vue')
    }
};
</script>
