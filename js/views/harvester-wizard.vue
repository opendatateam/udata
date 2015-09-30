<template>
<wizard v-ref="wizard" steps="{{steps}}"></wizard>
</template>

<script>
import HarvestSource from 'models/harvest/source';

export default {
    data: function() {
        return {
            meta: {
                title:this._('New harvester'),
            },
            source: new HarvestSource(),
            publish_as: null,
            steps: [{
                label: this._('Harvest as'),
                subtitle: this._('Choose who is harvesting'),
                component: 'publishas',
                next: (component) => {
                    if (component.selected) {
                        this.publish_as = component.selected;
                    }
                    return true;
                }
            }, {
                label: this._('New harvester'),
                subtitle: this._('Configure your harvester'),
                component: 'harvest-form',
                next: (component) => {
                    if (component.$.form.validate()) {
                        Object.assign(this.source, component.serialize());
                        if (this.publish_as) {
                            this.source.organization = this.publish_as;
                        }
                        this.source.save();
                        this.source.$once('updated', () => {
                            this.$.wizard.go_next();
                        });
                        return false;
                    }
                }
            }, {
                label: this._('Done'),
                subtitle: this._('Your harvester is ready'),
                component: 'created',
                init: (component) => {
                    component.source = this.source;
                }
            }],
         };
    },
    components: {
        'harvest-form': require('components/harvest/form.vue'),
        publishas: require('components/widgets/publish-as.vue'),
        created: require('components/harvest/created.vue'),
        wizard: require('components/widgets/wizard.vue'),
    },
    events: {
        'wizard:next-step': function() {
            this.$.wizard.go_next();
        },
        'wizard:previous-step': function() {
            this.$.wizard.go_previous();
        },
        'wizard:step-changed': function() {
            this.$.wizard.$.content.source = this.source;
        }
    }
};
</script>
