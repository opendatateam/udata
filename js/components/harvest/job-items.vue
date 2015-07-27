<style lang="less">
</style>

<template>
<datatable icon="cog"
    loading="{{job.loading}}"
    fields="{{ fields }}"
    p="{{ p }}" track="false"
    bodyclass="table-responsive no-padding">
    <aside><span>dataset</span></aside>
</datatable>
</template>

<script>
import {HarvestJob} from 'models/harvest/job';
import {STATUS_CLASSES, STATUS_I18N} from 'models/harvest/item';
import {PageList} from 'models/base';

export default {
    name: 'JobDetails',
    props: ['job'],
    components: {
        'datatable': require('components/widgets/datatable.vue'),
    },
    data: function() {
        return {
            job: new HarvestJob(),
            fields: [{
                label: this._('Remote Id'),
                key: 'remote_id',
                sort: 'remote_id'
            }, {
                label: this._('Status'),
                key: 'status',
                type: 'label',
                label_type: function(status) {
                    return STATUS_CLASSES[status];
                },
                label_func: function(status) {
                    return STATUS_I18N[status];
                }
            }, {
                label: this._('Started at'),
                key: 'started',
                sort: 'started',
                type: 'datetime'
            }, {
                label: this._('Ended'),
                key: 'ended',
                sort: 'ended',
                type: 'datetime'
            }]
        };
    },
    computed: {
        p: function() {
            return new PageList({data: this.job.items});
        }
    },
    events: {
        'datatable:item:click': function(item) {
            this.$dispatch('harvest:job:item:selected', item);
        }
    }
};
</script>
