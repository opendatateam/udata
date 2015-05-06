<style lang="less">
</style>

<template>
<wizard-component v-ref="wizard" steps="{{steps}}"></wizard-component>
</template>

<script>
'use strict';

var Dataset = require('models/dataset'),
    Vue = require('vue');

module.exports = {
    paramAttributes: ['dataset'],
    data: function() {
        return {
            meta: {
                title:this._('New dataset'),
                // subtitle: this._('Dataset')
            },
            dataset: new Dataset(),
            publish_as: null,
            steps: [{
                label: this._('Publish as'),
                subtitle: this._('Choose who is publishing'),
                component: 'publish-as',
                next: function(component) {
                    if (component.selected) {
                        this.publish_as = component.selected;
                    }
                    return true;
                }.bind(this)
            }, {
                label: this._('New dataset'),
                subtitle: this._('Describe your dataset'),
                component: 'create-form',
                next: function(component) {
                    if (component.$.form.validate()) {
                        this.dataset.$data = component.serialize();
                        if (this.publish_as) {
                            this.dataset.$data.organization = this.publish_as;
                        }
                        this.dataset.save();
                        this.dataset.$once('updated', function() {
                            this.$.wizard.go_next();
                        }.bind(this));
                        return false;
                    }
                }.bind(this)
            }, {
                label: this._('Resources'),
                subtitle: this._('Add your firsts resources'),
                component: 'resource-form',
                init: function(component) {
                    component.dataset = this.dataset;
                }.bind(this),
                next: function(component) {
                    if (component.validate()) {
                        var resource = component.serialize();
                        this.dataset.save_resource(resource);
                        this.dataset.$once('updated', function() {
                            this.$.wizard.go_next();
                        }.bind(this));
                        return false;
                    }
                }.bind(this)
            }, {
                label: this._('Share'),
                subtitle: this._('Communicate about your publication'),
                component: 'dataset-created',
                init: function(component) {
                    component.dataset = this.dataset;
                }.bind(this)
            }],
         };
    },
    components: {
        'wizard-component': require('components/widgets/wizard.vue'),
        'publish-as': require('components/widgets/publish-as.vue'),
        'create-form': require('components/dataset/create-form.vue'),
        'add-resource-form': require('components/dataset/add-resource-form.vue'),
        'resource-form': require('components/dataset/resource/form.vue'),
        'dataset-created': require('components/dataset/created.vue')
    },
    events: {
        'wizard:next-step': function() {
            this.$.wizard.go_next();
        },
        'wizard:previous-step': function() {
            this.$.wizard.go_previous();
        },
        'wizard:step-changed': function() {
            this.$.wizard.$.content.dataset = this.dataset;
        }
    }
};
</script>
