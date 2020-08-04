<template>
<div>
<datatable icon="cog"
    :title="title"
    bodyclass="table-responsive no-padding"
    :p="p" :track="false"
    :loading="loading !== undefined ? loading : job.loading"
    :fields="fields"
    track="remote_id"
    :empty="empty"
    :tint="job.status | statusClass">
    <div class="row" slot="header">
        <div class="col-xs-12" :class="{'col-lg-6': job.created}" v-show="withSlot">
            <slot></slot>
        </div>
        <dl class="dl-horizontal col-xs-12" :class="{'col-lg-6': withSlot}" v-show="job.created">
            <dt>{{ _('Created at') }}</dt>
            <dd>{{ job.created | dt }}</dd>
            <dt>{{ _('Ended at') }}</dt>
            <dd>{{ job.ended | dt }}</dd>
            <dt>{{ _('Status') }}</dt>
            <dd><span class="label label-{{ job.status | statusClass }}">{{ job.status | statusI18n }}</span></dd>
            <dt v-if="job.errors && job.errors.length">{{ _('Errors') }}</dt>
            <dd v-if="job.errors && job.errors.length">
                <div v-for="error in job.errors">
                    <p><strong>{{{error.message | markdown}}}</strong></p>
                    <div v-if="error.details">
                    <code><pre>{{error.details}}</pre></code>
                    </div>
                </div>
            </dd>
            <dt v-if="job.items && job.items.length">{{ _('Items') }}</dt>
            <dd v-if="job.items && job.items.length">
                <span class="text-warning" v-tooltip tooltip-placement="top"
                    :title="_('Number of skipped items')"
                    >{{job.items | count 'skipped'}}</span>
                /
                <span class="text-warning" v-tooltip tooltip-placement="top"
                    :title="_('Number of archived items')"
                    >{{job.items | count 'archived'}}</span>
                /
                <span class="text-danger" v-tooltip tooltip-placement="top"
                    :title="_('Number of failed items')"
                    >{{job.items | count 'failed'}}</span>
                /
                <span class="text-green" v-tooltip tooltip-placement="top"
                    :title="_('Number of succeed items')"
                    >{{job.items | count 'done'}}</span>
                /
                <strong>{{job.items.length}}</strong>
            </dd>
        </dl>
    </div>
</datatable>
</div>
</template>

<script>
import {
    STATUS_CLASSES as JOB_STATUS_CLASSES,
    STATUS_I18N as JOB_STATUS_I18N,
    HarvestJob
} from 'models/harvest/job';
import {STATUS_CLASSES, STATUS_I18N} from 'models/harvest/item';
import {PageList} from 'models/base';
import Datatable from 'components/datatable/widget.vue';

export default {
    name: 'JobDetails',
    props: {
        job: HarvestJob,
        loading: {
            type: Boolean,
            default: undefined
        },
        empty: String,
        withSlot: {type: Boolean, default: false}
    },
    components: {Datatable},
    data() {
        return {
            fields: [{
                label: this._('Remote ID'),
                key: 'remote_id',
                sort: 'remote_id',
                ellipsis: true
            }, {
                label: this._('Status'),
                key: 'status',
                sort: 'status',
                type: 'label',
                width: 100,
                label_type: (status) =>  STATUS_CLASSES[status],
                label_func: (status) => STATUS_I18N[status],
            }],
            p: new PageList({data: this.job.items}),
        };
    },
    computed: {
        title() {
            return this.job.id ? `Job ${this.job.id}` : 'Job';
        },
    },
    events: {
        'datatable:item:click': function(item) {
            this.$dispatch('harvest:job:item:selected', item);
        }
    },
    filters: {
        statusClass(value) {
            return JOB_STATUS_CLASSES[value] || '';
        },
        statusI18n(value) {
            return JOB_STATUS_I18N[value];
        },
        count(value, status) {
            if (!value) return '-';
            return value.filter(function(item) {
                return item.status === status;
            }).length;
        }
    },
    watch: {
        'job.items': function(items) {
            this.p = new PageList({data: items});
        }
    }
};
</script>
