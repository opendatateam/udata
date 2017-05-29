<template>
<div>
<wizard v-ref:wizard :steps="steps" :finish="true" :title="_('New Post')"></wizard>
</div>
</template>

<script>
import API from 'api';
import Post from 'models/post';

import Wizard from 'components/widgets/wizard.vue';

// Steps
import PostForm from 'components/post/form.vue';
import DatasetCardsForm from 'components/dataset/cards-form.vue';
import ReuseCardsForm from 'components/reuse/cards-form.vue';
import ImagePicker from 'components/widgets/image-picker.vue';


export default {
    name: 'post-wizard',
    components: {Wizard},
    data() {
        return {
            post: new Post(),
            steps: [{
                label: this._('Writing'),
                subtitle: this._('Write your post'),
                component: PostForm,
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
                component: DatasetCardsForm,
                next: (component) => {
                    this.post.datasets = component.datasets;
                    this.post.save();
                    return true;
                }
            }, {
                label: this._('Reuses'),
                subtitle: this._('Add some related reuses'),
                component: ReuseCardsForm,
                next: (component) => {
                    this.post.reuses = component.reuses;
                    this.post.save();
                    return true;
                }
            }, {
                label: this._('Image'),
                subtitle: this._('Upload your post image'),
                component: ImagePicker,
                init: (component) => {
                    const endpoint = API.posts.operations.post_image;
                    component.endpoint = endpoint.urlify({post: this.post.id});
                },
                next: (component) => {
                    component.save();
                    return true;
                }
            }]
         };
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
            this.$go({name: 'post', params: {oid: this.post.id}});
        }
    }
};
</script>
