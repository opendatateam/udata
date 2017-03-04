<template>
    <datatable :title="title" icon="tasks"
        boxclass="harvesters-widget"
        :fields="fields" :p="sources" :loading="sources.loading"
        :empty="_('No harvester')">
    </datatable>
</template>

<script>
import {Model} from 'models/base';
import HarvestSources from 'models/harvest/sources';
import {STATUS_CLASSES, STATUS_I18N} from 'models/harvest/job';
import Datatable from 'components/datatable/widget.vue';

const MASK = ['id', 'name', 'owner', 'last_job{status,ended}', 'organization'];

export default {
    MASK,
    components: {Datatable},
    props: {
        owner: {
            type: Model,
            default: () => {}
        }
    },
    data() {
        return {
            title: this._('Harvesters'),
            sources: new HarvestSources({mask: MASK}),
            fields: [{
                label: this._('Name'),
                key: 'name',
                sort: 'name',
                align: 'left',
                type: 'text'
            }, {
                label: this._('Status'),
                key: 'last_job.status',
                sort: 'last_job.status',
                type: 'label',
                width: 100,
                label_type(status) {
                    if (!status) return 'default';
                    return STATUS_CLASSES[status];
                },
                label_func: (status) => {
                    if (!status) return this._('No job yet');
                    return STATUS_I18N[status];
                }
            }, {
                label: this._('Last run'),
                key: 'last_job.ended',
                sort: 'last_job.ended',
                align: 'left',
                type: 'timeago',
                width: 120
            }]
        };
    },
    events: {
        'datatable:item:click': function(harvester) {
            this.$go('/harvester/' + harvester.id + '/');
        }
    },
    ready() {
        if (this.owner instanceof Model) {
            // Only fetch if binding occured and object is already fetched, else wait for watch
            if (this.owner.id) {
                this.sources.fetch({owner: this.owner.id});
            }
        } else {
            this.sources.fetch();
        }
    },
    watch: {
        'owner.id': function(ownerid) {
            this.sources.fetch({owner: ownerid});
        }
    }
};
</script>
