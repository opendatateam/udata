<template>
<div>
    <datatable :title="source.name || ''" icon="tasks"
        boxclass="harvest-jobs-widget"
        :fields="fields"
        :p="jobs"
        :loading="source.loading || jobs.loading"
        :empty="_('No job yet')">
        <header slot="header">
            {{{ source.description | markdown }}}
            <dl class="dl-horizontal">
                <dt v-if="source.owner">{{ _('Owner') }}</dt>
                <dd v-if="source.owner">
                    <a v-link="{name:'user', params: {oid: source.owner.id}}"
                        :title="source.owner | display">
                        <img class="avatar"
                            :src="source.owner | avatar_url AVATAR_SIZE"
                            :alt="source.owner | display"
                            :width="AVATAR_SIZE" :height="AVATAR_SIZE">
                        {{ source.owner | display }}
                    </a>
                </dd>
                <dt v-if="source.organization">{{ _('Organization') }}</dt>
                <dd v-if="source.organization">
                    <a v-link="{name:'organization', params: {oid: source.organization.id}}"
                        :title="source.organization | display">
                        <img class="avatar"
                            :src="source.organization | logo_url AVATAR_SIZE"
                            :alt="source.organization | display"
                            :width="AVATAR_SIZE" :height="AVATAR_SIZE">
                        {{ source.organization | display }}
                    </a>
                </dd>
                <dt>{{ _('Backend') }}</dt>
                <dd>{{ source.backend }}</dd>
                <dt>{{ _('URL') }}</dt>
                <dd>{{ source.url }}</dd>
                <dt>{{ _('Scheduling') }}</dt>
                <dd v-if="source.schedule">{{ source.schedule }}</dd>
                <dd v-else>{{ _('Not scheduled') }}</dd>
                <dt>{{ _('Jobs') }}</dt>
                <dd>{{ jobs.total }}</dd>
            </dl>
        </header>
    </datatable>
</div>
</template>

<script>
import {STATUS_CLASSES, STATUS_I18N} from 'models/harvest/job';
import Datatable from 'components/datatable/widget.vue';
import HarvestJobs from 'models/harvest/jobs';

const MASK = ['id', 'created', 'status'];
const AVATAR_SIZE = 20

export default {
    components: {Datatable},
    props: {
        source: Object,
        current: null
    },
    data() {
        return {
            AVATAR_SIZE,
            title: this._('Jobs'),
            jobs: new HarvestJobs({query: {page_size: 10}, mask: MASK}),
            fields: [{
                label: this._('Date'),
                key: 'created',
                sort: 'created',
                type: 'datetime'
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
            }]
        };
    },
    events: {
        'datatable:item:click': function(item) {
            this.$dispatch('harvest:job:selected', item);
            return true;
        }
    },
    watch: {
        'source.id': function(id) {
            if (id) {
                this.jobs.fetch({ident: id});
            }
        }
    }
};
</script>
