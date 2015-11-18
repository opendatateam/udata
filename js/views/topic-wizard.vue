<template>
<wizard v-ref:wizard :steps="steps" :finish="true" :title="_('New topic')"></wizard>
</template>

<script>
import Topic from 'models/topic';

export default {
    data: function() {
        return {
            topic: new Topic(),
            steps: [{
                label: this._('Writing'),
                subtitle: this._('Write your topic'),
                component: require('components/topic/form.vue'),
                next: (component) => {
                    if (component.$refs.form.validate()) {
                        Object.assign(this.topic, component.$refs.form.serialize());
                        this.topic.save();
                        return true;
                    }
                }
            }, {
                label: this._('Datasets'),
                subtitle: this._('Add some related datasets'),
                component: require('components/dataset/cards-form.vue'),
                next: (component) => {
                    this.topic.datasets = component.datasets;
                    this.topic.save();
                    return true;
                }
            }, {
                label: this._('Reuses'),
                subtitle: this._('Add some related reuses'),
                component: require('components/reuse/cards-form.vue'),
                next: (component) => {
                    this.topic.reuses = component.reuses;
                    this.topic.save();
                    return true;
                }
            }]
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
            this.$refs.wizard.$refs.content.topic = this.topic;
        },
        'wizard:finish': function() {
            this.$go('/topic/' + this.topic.id);
        }
    }
};
</script>
