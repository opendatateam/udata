<template>
    <datatable title="{{ title }}" icon="tasks"
        boxclass="harvesters-widget"
        fields="{{ fields }}" p="{{ sources }}"
        empty="{{ _('No harvester') }}">
    </datatable>
</template>

<script>
import sources from 'models/harvest/sources';

export default {
    name: 'harvesters-widget',
    components: {
        datatable: require('components/widgets/datatable.vue')
    },
    data: function() {
        return {
            title: this._('Harvesters'),
            sources: sources,
            fields: [{
                label: this._('Name'),
                key: 'name',
                sort: 'name',
                align: 'left',
                type: 'text'
            }, {
                label: this._('Description'),
                key: 'description',
                sort: 'description',
                align: 'left',
                type: 'text'
            }, {
                label: '',
                key: 'enabled',
                // sort: 'name',
                // align: 'left',
                type: 'playpause',
                width: '20px'
            }]
        };
    },
    events: {
        'datatable:item:click': function(harvester) {
            this.$go('/harvester/' + harvester.id + '/');
        }
    }
};
</script>
