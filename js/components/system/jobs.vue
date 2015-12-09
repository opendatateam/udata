<template>
    <datatable :title="title" icon="cogs"
        boxclass="jobs-widget"
        :fields="fields" :p="jobs"
        :empty="_('No job')">
    </datatable>
</template>

<script>
import jobs from 'models/jobs';

export default {
    name: 'jobs-widget',
    components: {
        datatable: require('components/datatable/widget.vue')
    },
    data: function() {
        return {
            title: this._('Jobs'),
            jobs: jobs,
            fields: [{
                label: this._('Name'),
                key: 'name',
                sort: 'name',
                align: 'left',
                type: 'text'
            }, {
                label: this._('Schedule'),
                key: 'schedule',
                sort: 'schedule',
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
        'datatable:item:click': function(job) {
            this.$go('/job/' + job.id + '/');
        }
    }
};
</script>
