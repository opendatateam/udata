<template>
<wizard v-ref:wizard :steps="steps"></wizard>
</template>

<script>
import Dataset from 'models/dataset';
import Vue from 'vue';

export default {
    props: {
        dataset: {
            type: Dataset,
            default: function() {
                return new Dataset();
            }
        }
    },
    data: function() {
        return {
            meta: {
                title:this._('New dataset'),
                // subtitle: this._('Dataset')
            },
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
                label: this._('New dataset'),
                subtitle: this._('Describe your dataset'),
                component: 'create-form',
                next: (component) => {
                    if (component.validate()) {
                        let data = component.serialize();
                        if (this.publish_as) {
                            data.organization = this.publish_as;
                        }
                        Object.assign(this.dataset, data);
                        this.dataset.save();
                        this.dataset.$once('updated', () => {
                            this.$refs.wizard.go_next();
                        });
                        return false;
                    }
                }
            }, {
                label: this._('Resources'),
                subtitle: this._('Add your firsts resources'),
                component: 'resource-form',
                init: (component) => {
                    component.dataset = this.dataset;
                },
                next: (component) => {
                    if (component.validate()) {
                        var resource = component.serialize();
                        this.dataset.save_resource(resource);
                        this.dataset.$once('updated', () => {
                            this.$refs.wizard.go_next();
                        });
                        return false;
                    }
                }
            }, {
                label: this._('Share'),
                subtitle: this._('Communicate about your publication'),
                component: 'dataset-created',
                init: (component) => {
                    component.dataset = this.dataset;
                }
            }],
         };
    },
    components: {
        wizard: require('components/widgets/wizard.vue'),
        'publish-as': require('components/widgets/publish-as.vue'),
        'create-form': require('components/dataset/form.vue'),
        'add-resource-form': require('components/dataset/add-resource-form.vue'),
        'resource-form': require('components/dataset/resource/form.vue'),
        'dataset-created': require('components/dataset/created.vue')
    },
    events: {
        'wizard:next-step': function() {
            this.$refs.wizard.go_next();
        },
        'wizard:previous-step': function() {
            this.$refs.wizard.go_previous();
        },
        'wizard:step-changed': function() {
            this.$refs.wizard.$refs.content.dataset = this.dataset;
        }
    },
    route: {
        activate() {
            this.$dispatch('meta:updated', this.meta);
        }
    }
};
</script>
