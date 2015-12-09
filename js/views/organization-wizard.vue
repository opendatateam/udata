<template>
<wizard v-ref:wizard :steps="steps" :title="_('New organization')"></wizard>
</template>

<script>
import Organization from 'models/organization';
import API from 'api';

export default {
    data: function() {
        return {
            organization: new Organization(),
            steps: [{
                label: this._('Verification'),
                subtitle: this._('Ensure your organization does not exists'),
                component: require('components/organization/pre-create.vue'),
            }, {
                label: this._('Description'),
                subtitle: this._('Describe your organization'),
                component: require('components/organization/form.vue'),
                next: (component) => {
                    if (component.validate()) {
                        let data = component.serialize();
                        Object.assign(this.organization, data);
                        this.organization.save();
                        this.organization.$once('updated', () => {
                            this.$refs.wizard.go_next();
                        });
                        return false;
                    }
                }
            }, {
                label: this._('Logo'),
                subtitle: this._('Upload your organization logo'),
                component: require('components/widgets/image-picker.vue'),
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
                component: require('components/organization/post-create.vue'),
                init: (component) => {
                    component.organization = this.organization;
                }
            }],
         };
    },
    props: ['orgid'],
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
            this.$refs.wizard.$refs.content.organization = this.organization;
        },
        'image:saved': function() {
            this.organization.fetch();
            this.$refs.wizard.go_next();
        }
    }
};
</script>
