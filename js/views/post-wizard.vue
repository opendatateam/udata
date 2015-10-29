<template>
<wizard-component v-ref:wizard steps="{{steps}}" finish="true"></wizard-component>
</template>

<script>
import API from 'api';
import Post from 'models/post';

export default {
    data: function() {
        return {
            meta: {
                title:this._('New post')
            },
            post: new Post(),
            steps: [{
                label: this._('Writing'),
                subtitle: this._('Write your post'),
                component: 'post-form',
                next: (component) => {
                    if (component.$.form.validate()) {
                        Object.assign(this.post, component.$.form.serialize());
                        this.post.save();
                        return true;
                    }
                }
            }, {
                label: this._('Datasets'),
                subtitle: this._('Add some related datasets'),
                component: 'dataset-cards-form',
                next: (component) => {
                    this.post.datasets = component.datasets;
                    this.post.save();
                    return true;
                }
            }, {
                label: this._('Reuses'),
                subtitle: this._('Add some related reuses'),
                component: 'reuse-cards-form',
                next: (component) => {
                    this.post.reuses = component.reuses;
                    this.post.save();
                    return true;
                }
            }, {
                label: this._('Image'),
                subtitle: this._('Upload your post image'),
                component: 'image-picker',
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
        'wizard-component': require('components/widgets/wizard.vue'),
        'post-form': require('components/post/form.vue'),
        'image-picker': require('components/widgets/image-picker.vue'),
        'dataset-cards-form': require('components/dataset/cards-form.vue'),
        'reuse-cards-form': require('components/reuse/cards-form.vue')
    },
    events: {
        'wizard:next-step': function() {
            this.$refs.wizard.go_next();
        },
        'wizard:previous-step': function() {
            this.$refs.wizard.go_previous();
        },
        'wizard:step-changed': function() {
            this.$refs.wizard.$.content.post = this.post;
        },
        'wizard:finish': function() {
            this.$go('/post/' + this.post.id);
        }
    }
};
</script>
