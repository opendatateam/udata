<template>
<wizard-component v-ref="wizard" steps="{{steps}}"></wizard-component>
</template>

<script>
import Organization from 'models/organization';
import API from 'api';

export default {
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
                next: (component) => {
                    if (component.validate()) {
                        let data = component.serialize();
                        Object.assign(this.organization, data);
                        this.organization.save();
                        this.organization.$once('updated', () => {
                            this.$.wizard.go_next();
                        });
                        return false;
                    }
                }.bind(this)
            }, {
                label: this._('Logo'),
                subtitle: this._('Upload your organization logo'),
                component: 'image-picker',
                init: (component) => {
                    var endpoint = API.organizations.operations.organization_logo;
                    component.endpoint = endpoint.urlify({org: this.organization.id});
                },
                next: (component) => {
                    component.save();
                    return false;
                }
            }, {
                label: this._('Publish'),
                subtitle: this._('Publish some content'),
                component: 'post-create',
                init: (component) => {
                    component.organization = this.organization;
                }
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
    }
};
</script>
