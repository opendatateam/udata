<template>
<div>
<wizard v-ref:wizard :steps="steps" :title="_('New harvester')"></wizard>
</div>
</template>

<script>
import HarvestSource from 'models/harvest/source';
import Wizard from 'components/widgets/wizard.vue';

// Steps
import PublishAs from 'components/widgets/publish-as.vue';
import HarvesterForm from 'components/harvest/form.vue';
import HarvesterCreated from 'components/harvest/created.vue';

export default {
    name: 'harvester-wizard',
    components: {Wizard},
    data() {
        return {
            source: new HarvestSource(),
            publish_as: null,
            steps: [{
                label: this._('Harvest as'),
                subtitle: this._('Choose who is harvesting'),
                component: PublishAs,
                next: (component) => {
                    if (component.selected) {
                        this.publish_as = component.selected;
                    }
                    return true;
                }
            }, {
                label: this._('New harvester'),
                subtitle: this._('Configure your harvester'),
                component: HarvesterForm,
                init: (component) => {
                    this.source.$once('updated', () => {
                        this.$refs.wizard.go_next();
                    });
                },
                next: (component) => {
                    if (component.$refs.form.validate()) {
                        Object.assign(this.source, component.serialize());
                        if (this.publish_as) {
                            this.source.organization = this.publish_as;
                        }
                        this.source.save(component.on_error);
                        return false;
                    }
                }
            }, {
                label: this._('Done'),
                subtitle: this._('Your harvester is ready'),
                component: HarvesterCreated,
                init: (component) => {
                    component.source = this.source;
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
            this.$refs.wizard.$refs.content.source = this.source;
        }
    }
};
</script>
