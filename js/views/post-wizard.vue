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
                        this.post.$data = component.$.form.serialize();
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
    // props: ['orgid'],
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
    // created: function() {
    //     console.log('created', this.$router, this.$options.routes);
    // },
    // routes: {
    //     '/': function() {
    //         this.step_index = 0;
    //         // this.loadView('organization-wizard');
    //     },
    //     '/:oid': {
    //         on: function(oid) {
    //             if (oid != this.organization.id) {
    //                 this.organization.fetch(oid);
    //             }
    //         },
    //         '/': function() {
    //             this.step_index = 1;
    //         },
    //         '/publish': function(oid) {
    //             this.step_index = 2;
    //         }
    //     }
    // }
};
</script>
