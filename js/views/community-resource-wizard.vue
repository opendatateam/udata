<template>
<wizard v-ref:wizard :steps="steps"></wizard>
</template>

<script>
import CommunityResource from 'models/communityresource';
import Dataset from 'models/dataset';
import API from 'api';

export default {
    data: function() {
        return {
            meta: {
                title: this._('New community resource'),
            },
            communityResource: new CommunityResource(),
            dataset: new Dataset(),
            publish_as: null,
            steps: [{
                label: this._('Publish as'),
                subtitle: this._('Choose who is publishing'),
                component: 'publish-as',
                next: (component) => {
                    if (component.selected) {
                        this.publish_as = component.selected;
                    }
                    return true;
                }
            }, {
                label: this._('Resources'),
                subtitle: this._('Describe your community resource'),
                component: 'resource-form',
                init: (component) => {
                    this.dataset_id = this.$route.query.dataset_id;
                    this.dataset.fetch(this.dataset_id);
                    component.dataset = this.dataset;
                    component.community = true;
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
                component: 'post-create',
                init: (component) => {
                    this.communityResource._set('url', this.dataset.page + '#resource-' + this.communityResource.id);
                    component.communityResource = this.communityResource;
                }
            }],
         };
    },
    components: {
        'resource-form': require('components/dataset/resource/form.vue'),
        'dataset-cards-form': require('components/dataset/cards-form.vue'),
        'image-picker': require('components/widgets/image-picker.vue'),
        'post-create': require('components/communityresource/post-create.vue'),
        'publish-as': require('components/widgets/publish-as.vue'),
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
            this.$refs.wizard.$.content.communityResource = this.communityResource;
        }
    },
    route: {
        activate() {
            this.$dispatch('meta:updated', this.meta);
        }
    }
};
</script>
