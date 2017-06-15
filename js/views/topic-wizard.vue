<template>
<div>
<wizard v-ref:wizard :steps="steps" :finish="true" :title="_('New topic')"></wizard>
</div>
</template>

<script>
import Topic from 'models/topic';

import Wizard from 'components/widgets/wizard.vue';

// Steps
import TopicForm from 'components/topic/form.vue';
import DatasetCardsForm from 'components/dataset/cards-form.vue';
import ReuseCardsForm from 'components/reuse/cards-form.vue';


export default {
    name: 'topic-wizard',
    components: {Wizard},
    data() {
        return {
            topic: new Topic(),
            steps: [{
                label: this._('Writing'),
                subtitle: this._('Write your topic'),
                component: TopicForm,
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
                component: DatasetCardsForm,
                next: (component) => {
                    this.topic.datasets = component.datasets;
                    this.topic.save();
                    return true;
                }
            }, {
                label: this._('Reuses'),
                subtitle: this._('Add some related reuses'),
                component: ReuseCardsForm,
                next: (component) => {
                    this.topic.reuses = component.reuses;
                    this.topic.save();
                    return true;
                }
            }]
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
            this.$refs.wizard.$refs.content.topic = this.topic;
        },
        'wizard:finish': function() {
            this.$go({name: 'topic', params: {oid: this.topic.id}});
        }
    }
};
</script>
