<template>
<div>
<wizard v-ref:wizard :steps="steps" :title="_('New dataset')"></wizard>
</div>
</template>

<script>
import Dataset from 'models/dataset';
import Vue from 'vue';
import Wizard from 'components/widgets/wizard.vue';
// Steps
import PublishAs from 'components/widgets/publish-as.vue';
import DatasetForm from 'components/dataset/form.vue';
import ResourceForm from 'components/dataset/resource/form.vue';
import Share from 'components/dataset/created.vue';


export default {
    name: 'dataset-wizard',
    components: {Wizard},
    props: {
        dataset: {
            type: Dataset,
            default() {
                return new Dataset();
            }
        }
    },
    data() {
        return {
            publish_as: null,
            steps: [{
                label: this._('Publish as'),
                subtitle: this._('Choose who is publishing'),
                component: PublishAs,
                next: (component) => {
                    if (component.selected) {
                        this.publish_as = component.selected;
                    }
                    return true;
                }
            }, {
                label: this._('New dataset'),
                subtitle: this._('Describe your dataset'),
                component: DatasetForm,
                next: (component) => {
                    if (component.validate()) {
                        const data = component.serialize();
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
                subtitle: this._('Add your first resources'),
                component: ResourceForm,
                init: (component) => {
                    component.dataset = this.dataset;
                    component.isUpload = true;
                },
                next: (component) => {
                    if (component.validate()) {
                        const resource = component.serialize();
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
                component: Share,
                init: (component) => {
                    component.dataset = this.dataset;
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
            this.$refs.wizard.$refs.content.dataset = this.dataset;
        }
    }
};
</script>
