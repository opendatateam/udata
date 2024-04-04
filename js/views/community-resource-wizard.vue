<template>
<wizard v-ref:wizard :steps="steps" :title="_('New community resource')"></wizard>
</template>

<script>
import CommunityResource from 'models/communityresource';
import Dataset from 'models/dataset';
import API from 'api';

export default {
    data: function() {
        return {
            communityResource: new CommunityResource({data: {filetype: 'remote', type: 'main'}}),
            dataset: new Dataset(),
            publish_as: null,
            steps: [{
                label: this._('Publish as'),
                subtitle: this._('Choose who is publishing'),
                component: require('components/widgets/publish-as.vue'),
                next: (component) => {
                    if (component.selected) {
                        this.publish_as = component.selected;
                    }
                    return true;
                }
            }, {
                label: this._('Resources'),
                subtitle: this._('Describe your community resource'),
                component: require('components/dataset/resource/form.vue'),
                init: (component) => {
                    this.dataset_id = this.$route.query.dataset_id;
                    this.dataset.fetch(this.dataset_id);
                    component.dataset = this.dataset;
                    component.resource = this.communityResource;
                    component.isUpload = true;
                },
                next: (component) => {
                    if (component.validate()) {
                        let data = component.serialize();
                        if (this.publish_as) {
                            data.organization = this.publish_as;
                        }
                        Object.assign(this.communityResource, data);
                        this.communityResource.dataset = this.dataset_id;
                        this.communityResource.save();
                        this.communityResource.$once('updated', () => {
                            this.$refs.wizard.go_next();
                        });
                        return false;
                    }
                }
            }, {
                label: this._('Share'),
                subtitle: this._('Communicate about your publication'),
                component: require('components/dataset/communityresource/post-create.vue'),
                init: (component) => {
                    this.communityResource._set('url', this.dataset.page + '#resource-community-' + this.communityResource.id);
                    component.communityResource = this.communityResource;
                }
            }],
         };
    },
    components: {
        wizard: require('components/widgets/wizard.vue'),
    },
    events: {
        'wizard:next-step': function() {
            this.$refs.wizard.go_next();
        },
        'wizard:previous-step': function() {
            this.$refs.wizard.go_previous();
        },
        'wizard:step-changed': function() {
            this.$refs.wizard.$refs.content.communityResource = this.communityResource;
        }
    }
};
</script>
