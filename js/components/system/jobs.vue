<template>
<div>
    <datatable :title="title" icon="cogs"
        boxclass="jobs-widget"
        :fields="fields" :p="jobs"
        :empty="_('No job')">
    </datatable>
</div>
</template>

<script>
import jobs from 'models/jobs';
import Datatable from 'components/datatable/widget.vue';

export default {
    name: 'jobs-list',
    components: {Datatable},
    data() {
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
                label: this._('Scheduling'),
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
