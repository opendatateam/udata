<template>
<wizard v-ref:wizard :steps="steps" :finish="true"></wizard>
</template>

<script>
import Topic from 'models/topic';

export default {
    data: function() {
        return {
            meta: {
                title:this._('New topic')
            },
            topic: new Topic(),
            steps: [{
                label: this._('Writing'),
                subtitle: this._('Write your topic'),
                component: 'topic-form',
                next: (component) => {
                    if (component.$.form.validate()) {
                        Object.assign(this.topic, component.$.form.serialize());
                        this.topic.save();
                        return true;
                    }
                }
            }, {
                label: this._('Datasets'),
                subtitle: this._('Add some related datasets'),
                component: 'dataset-cards-form',
                next: (component) => {
                    this.topic.datasets = component.datasets;
                    this.topic.save();
                    return true;
                }
            }, {
                label: this._('Reuses'),
                subtitle: this._('Add some related reuses'),
                component: 'reuse-cards-form',
                next: (component) => {
                    this.topic.reuses = component.reuses;
                    this.topic.save();
                    return true;
                }
            }]
         };
    },
    components: {
        wizard: require('components/widgets/wizard.vue'),
        'topic-form': require('components/topic/form.vue'),
        'dataset-cards-form': require('components/dataset/cards-form.vue'),
        'reuse-cards-form': require('components/reuse/cards-form.vue')
    },
    events: {
        'wizard:next-step': function() {
            this.$refs.wizard.go_next();
        },
        'wizard:previous-step': function() {
            this.$refs.wizard.go_previous();
        },
        'wizard:step-changed': function() {
            this.$refs.wizard.$.content.topic = this.topic;
        },
        'wizard:finish': function() {
            this.$go('/topic/' + this.topic.id);
        }
    },
    route: {
        activate() {
            this.$dispatch('meta:updated', this.meta);
        }
    }
};
</script>
