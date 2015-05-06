<style lang="less">

</style>

<template>
<wizard-component v-ref="wizard" steps="{{steps}}"></wizard-component>
</template>

<script>
'use strict';

var Reuse = require('models/reuse'),
    API = require('api');

module.exports = {
    data: function() {
        return {
            meta: {
                title:this._('New reuse'),
                // subtitle: this._('reuse')
            },
            reuse: new Reuse(),
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
                label: this._('New reuse'),
                subtitle: this._('Describe your reuse'),
                component: 'create-form',
                next: function(component) {
                    if (component.$.form.validate()) {
                        this.reuse.$data = component.$.form.serialize();
                        if (this.publish_as) {
                            this.reuse.$data.organization = this.publish_as;
                        }
                        this.reuse.save();
                        this.reuse.$once('updated', function() {
                            this.$.wizard.go_next();
                        }.bind(this));
                        return false;
                    }
                }.bind(this)
            }, {
                label: this._('Datasets'),
                subtitle: this._('Add some related datasets'),
                component: 'dataset-cards-form',
                next: function(component) {
                    this.reuse.datasets = component.datasets;
                    this.reuse.save();
                        this.reuse.$once('updated', function() {
                            this.$.wizard.go_next();
                        }.bind(this));
                        return false;
                }.bind(this)
            }, {
                label: this._('Image'),
                subtitle: this._('Upload your reuse thumbnail'),
                component: 'image-picker',
                init: function(component) {
                    var endpoint = API.reuses.operations.reuse_image;
                    component.endpoint = endpoint.urlify({reuse: this.reuse.id});
                }.bind(this),
                next: function(component) {
                    component.save();
                    return false;
                }.bind(this)
            }, {
                label: this._('Share'),
                subtitle: this._('Communicate about your publication'),
                component: 'post-create',
                init: function(component) {
                    component.reuse = this.reuse;
                }.bind(this)
            }],
         };
    },
    components: {
        'create-form': require('components/reuse/create-form.vue'),
        'dataset-cards-form': require('components/dataset/cards-form.vue'),
        'image-picker': require('components/widgets/image-picker.vue'),
        'post-create': require('components/reuse/post-create.vue'),
        'publish-as': require('components/widgets/publish-as.vue'),
        'wizard-component': require('components/widgets/wizard.vue'),
    },
    events: {
        'wizard:next-step': function() {
            this.$.wizard.go_next();
        },
        'wizard:previous-step': function() {
            this.$.wizard.go_previous();
        },
        'wizard:step-changed': function() {
            this.$.wizard.$.content.reuse = this.reuse;
        },
        'image:saved': function() {
            this.reuse.fetch();
            this.$.wizard.go_next();
            return false;
        }
    }
};
</script>
