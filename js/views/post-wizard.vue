<template>
<wizard v-ref:wizard :steps="steps" :finish="true" :title="_('New Post')"></wizard>
</template>

<script>
import API from 'api';
import Post from 'models/post';

export default {
    data: function() {
        return {
            post: new Post(),
            steps: [{
                label: this._('Writing'),
                subtitle: this._('Write your post'),
                component: require('components/post/form.vue'),
                next: (component) => {
                    if (component.$refs.form.validate()) {
                        Object.assign(this.post, component.$refs.form.serialize());
                        this.post.save();
                        return true;
                    }
                }
            }, {
                label: this._('Datasets'),
                subtitle: this._('Add some related datasets'),
                component: require('components/dataset/cards-form.vue'),
                next: (component) => {
                    this.post.datasets = component.datasets;
                    this.post.save();
                    return true;
                }
            }, {
                label: this._('Reuses'),
                subtitle: this._('Add some related reuses'),
                component: require('components/reuse/cards-form.vue'),
                next: (component) => {
                    this.post.reuses = component.reuses;
                    this.post.save();
                    return true;
                }
            }, {
                label: this._('Image'),
                subtitle: this._('Upload your post image'),
                component: require('components/widgets/image-picker.vue'),
                init: (component) => {
                    var endpoint = API.posts.operations.post_image;
                    component.endpoint = endpoint.urlify({post: this.post.id});
                },
                next: (component) => {
                    component.save();
                    return true;
                }
            }]
         };
    },
    components: {
        wizard: require('components/widgets/wizard.vue')
    },
    events: {
        'wizard:next-step': function() {
            this.$refs.wizard.go_next();
        },
        'wizard:previous-step': function() {
            this.$refs.wizard.go_previous();
        },
        'wizard:step-changed': function() {
            this.$refs.wizard.$refs.content.post = this.post;
        },
        'wizard:finish': function() {
            this.$go('/post/' + this.post.id);
        }
    }
};
</script>
