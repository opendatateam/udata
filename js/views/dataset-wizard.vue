<template>
<wizard v-ref:wizard :steps="steps" :title="_('New dataset')"></wizard>
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
                label: this._('New dataset'),
                subtitle: this._('Describe your dataset'),
                component: require('components/dataset/form.vue'),
                next: (component) => {
                    if (component.validate()) {
                        let data = component.serialize();
                        if (this.publish_as) {
                            data.organization = this.publish_as;
                        }
                        Object.assign(this.dataset, data);
                        this.dataset.save(component.on_error);
                        this.dataset.$once('updated', () => {
                            this.$refs.wizard.go_next();
                        });
                        return false;
                    }
                }
            }, {
                label: this._('Resources'),
                subtitle: this._('Add your firsts resources'),
                component: require('components/dataset/resource/form.vue'),
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
                component: require('components/dataset/created.vue'),
                init: (component) => {
                    component.dataset = this.dataset;
                }
            }],
         };
    },
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
            this.$refs.wizard.$refs.content.dataset = this.dataset;
        }
    }
};
</script>
