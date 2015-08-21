<style lang="less">

</style>

<template>
<wizard-component v-ref="wizard" steps="{{steps}}"></wizard-component>
</template>

<script>
'use strict';

var Organization = require('models/organization'),
    API = require('api');

module.exports = {
    data: function() {
        return {
            meta: {
                title:this._('New organization'),
                // subtitle: this._('organization')
            },
            organization: new Organization(),
            steps: [{
                label: this._('Verification'),
                subtitle: this._('Ensure your organization does not exists'),
                component: 'pre-create'
            }, {
                label: this._('Description'),
                subtitle: this._('Describe your organization'),
                component: 'create-form',
                next: function(component) {
                    if (component.$.form.validate()) {
                        this.organization.$data = component.$.form.serialize();
                        this.organization.save();
                        this.organization.$once('updated', function() {
                            this.$.wizard.go_next();
                        }.bind(this));
                        return false;
                    }
                }.bind(this)
            }, {
                label: this._('Logo'),
                subtitle: this._('Upload your organization logo'),
                component: 'image-picker',
                init: function(component) {
                    var endpoint = API.organizations.operations.organization_logo;
                    component.endpoint = endpoint.urlify({org: this.organization.id});
                }.bind(this),
                next: function(component) {
                    component.save();
                    return false;
                }.bind(this)
            }, {
                label: this._('Publish'),
                subtitle: this._('Publish some content'),
                component: 'post-create',
                init: function(component) {
                    component.dataset = this.dataset;
                }.bind(this)
            }],
         };
    },
    props: ['orgid'],
    components: {
        'wizard-component': require('components/widgets/wizard.vue'),
        'pre-create': require('components/organization/pre-create.vue'),
        'create-form': require('components/organization/form.vue'),
        'post-create': require('components/organization/post-create.vue'),
        'image-picker': require('components/widgets/image-picker.vue')
    },
    events: {
        'wizard:next-step': function() {
            this.$.wizard.go_next();
        },
        'wizard:previous-step': function() {
            this.$.wizard.go_previous();
        },
        'wizard:step-changed': function() {
            this.$.wizard.$.content.organization = this.organization;
        },
        'image:saved': function() {
            this.organization.fetch();
            this.$.wizard.go_next();
            return false;
        }
    },
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
