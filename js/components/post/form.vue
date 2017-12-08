<template>
<div>
    <vform v-ref:form :fields="fields" :model="post"></vform>
</div>
</template>

<script>
import Post from 'models/post';

export default {
    name: 'post-form',
    components: {
            vform: require('components/form/vertical-form.vue')
    },
    props: {
        post: {type: Post, default: () => new Post()},
        hideNotifications: false
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
            const isValid = this.$refs.form.validate();

            if (isValid & !this.hideNotifications) {
                this.$dispatch('notify', {
                    autoclose: true,
                    title: this._('Changes saved'),
                    details: this._('Your post has been updated.')
                });
            }
            return isValid;
        }
    }
};
</script>
