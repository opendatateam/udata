<template>
<div>
<wizard v-ref:wizard :steps="steps" :title="_('New organization')"></wizard>
</div>
</template>

<script>
import Organization from 'models/organization';
import API from 'api';
import Wizard from 'components/widgets/wizard.vue';
// Steps
import PreCreate from 'components/organization/pre-create.vue';
import OrganizationForm from 'components/organization/form.vue';
import ImagePicker from 'components/widgets/image-picker.vue';
import PostCreate from 'components/organization/post-create.vue';

export default {
    name: 'organization-wizard',
    components: {Wizard},
    props: ['orgid'],
    data() {
        return {
            organization: new Organization(),
            steps: [{
                label: this._('Verification'),
                subtitle: this._('Ensure your organization does not exists'),
                component: PreCreate,
            }, {
                label: this._('Description'),
                subtitle: this._('Describe your organization'),
                component: OrganizationForm,
                init: (component) => {
                    this.organization.$once('updated', () => {
                        this.$refs.wizard.go_next();
                    });
                },
                next: (component) => {
                    if (component.validate()) {
                        const data = component.serialize();
                        Object.assign(this.organization, data);
                        this.organization.save(component.on_error);
                        return false;
                    }
                }
            }, {
                label: this._('Logo'),
                subtitle: this._('Upload your organization logo'),
                component: ImagePicker,
                init: (component) => {
                    const endpoint = API.organizations.operations.organization_logo;
                    component.endpoint = endpoint.urlify({org: this.organization.id});
                },
                next: (component) => {
                    component.save();
                    return false;
                }
            }, {
                label: this._('Publish'),
                subtitle: this._('Publish some content'),
                component: PostCreate,
                init: (component) => {
                    component.organization = this.organization;
                }
            }],
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
            this.$refs.wizard.$refs.content.organization = this.organization;
        },
        'image:saved': function() {
            this.organization.fetch();
            this.$refs.wizard.go_next();
        }
    }
};
</script>
