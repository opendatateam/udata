<template>
<wizard v-ref:wizard :steps="steps" :title="_('New reuse')"></wizard>
</template>

<script>
import Reuse from 'models/reuse';
import API from 'api';

export default {
    data: function() {
        return {
            reuse: new Reuse(),
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
                label: this._('New reuse'),
                subtitle: this._('Describe your reuse'),
                component: 'reuse-form',
                next: (component) => {
                    if (component.validate()) {
                        let data = component.serialize();
                        if (this.publish_as) {
                            data.organization = this.publish_as;
                        }
                        Object.assign(this.reuse, data);
                        this.reuse.save();
                        this.reuse.$once('updated', () => {
                            this.$refs.wizard.go_next();
                        });
                        return false;
                    }
                }
            }, {
                label: this._('Datasets'),
                subtitle: this._('Add some related datasets'),
                component: 'dataset-cards-form',
                next: (component) => {
                    this.reuse.datasets = component.datasets;
                    this.reuse.save();
                    this.reuse.$once('updated', () => {
                        this.$refs.wizard.go_next();
                    });
                    return false;
                }
            }, {
                label: this._('Image'),
                subtitle: this._('Upload your reuse thumbnail'),
                component: 'image-picker',
                init: (component) => {
                    var endpoint = API.reuses.operations.reuse_image;
                    component.endpoint = endpoint.urlify({reuse: this.reuse.id});
                },
                next: (component) => {
                    component.save();
                    return false;
                }
            }, {
                label: this._('Share'),
                subtitle: this._('Communicate about your publication'),
                component: 'post-create',
                init: (component) => {
                    component.reuse = this.reuse;
                }
            }],
         };
    },
    components: {
        'reuse-form': require('components/reuse/form.vue'),
        'dataset-cards-form': require('components/dataset/cards-form.vue'),
        'image-picker': require('components/widgets/image-picker.vue'),
        'post-create': require('components/reuse/post-create.vue'),
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
            this.$refs.wizard.$.content.reuse = this.reuse;
        },
        'image:saved': function() {
            this.reuse.fetch();
            this.$refs.wizard.go_next();
            return false;
        }
    }
};
</script>
