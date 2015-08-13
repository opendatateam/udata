<style lang="less">

</style>

<template>
<wizard-component v-ref="wizard" steps="{{steps}}" finish="true"></wizard-component>
</template>

<script>
'use strict';

var Post = require('models/post');

module.exports = {
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
                next: function(component) {
                    if (component.$.form.validate()) {
                        Object.assign(this.post, component.$.form.serialize());
                        this.post.save();
                        return true;
                    }
                }.bind(this)
            }, {
                label: this._('Datasets'),
                subtitle: this._('Add some related datasets'),
                component: 'dataset-cards-form',
                next: function(component) {
                    this.post.datasets = component.datasets;
                    this.post.save();
                    return true;
                }.bind(this)
            }, {
                label: this._('Reuses'),
                subtitle: this._('Add some related reuses'),
                component: 'reuse-cards-form',
                next: function(component) {
                    this.post.reuses = component.reuses;
                    this.post.save();
                    return true;
                }.bind(this)
            }]
         };
    },
    components: {
        'wizard-component': require('components/widgets/wizard.vue'),
        'post-form': require('components/post/form.vue'),
        'dataset-cards-form': require('components/dataset/cards-form.vue'),
        'reuse-cards-form': require('components/reuse/cards-form.vue')
    },
    events: {
        'wizard:next-step': function() {
            this.$.wizard.go_next();
        },
        'wizard:previous-step': function() {
            this.$.wizard.go_previous();
        },
        'wizard:step-changed': function() {
            this.$.wizard.$.content.post = this.post;
        },
        'wizard:finish': function() {
            this.$go('/post/' + this.post.id);
        }
    }
};
</script>
