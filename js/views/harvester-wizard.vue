<template>
<wizard v-ref:wizard :steps="steps" :title="_('New harvester')"></wizard>
</template>

<script>
import HarvestSource from 'models/harvest/source';

export default {
    data: function() {
        return {
            source: new HarvestSource(),
            publish_as: null,
            steps: [{
                label: this._('Harvest as'),
                subtitle: this._('Choose who is harvesting'),
                component: require('components/widgets/publish-as.vue'),
                next: (component) => {
                    if (component.selected) {
                        this.publish_as = component.selected;
                    }
                    return true;
                }
            }, {
                label: this._('New harvester'),
                subtitle: this._('Configure your harvester'),
                component: require('components/harvest/form.vue'),
                next: (component) => {
                    if (component.$refs.form.validate()) {
                        Object.assign(this.source, component.serialize());
                        if (this.publish_as) {
                            this.source.organization = this.publish_as;
                        }
                        this.source.save();
                        this.source.$once('updated', () => {
                            this.$refs.wizard.go_next();
                        });
                        return false;
                    }
                }
            }, {
                label: this._('Done'),
                subtitle: this._('Your harvester is ready'),
                component: require('components/harvest/created.vue'),
                init: (component) => {
                    component.source = this.source;
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
            this.$refs.wizard.$refs.content.source = this.source;
        }
    }
};
</script>
