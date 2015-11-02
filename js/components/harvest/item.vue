<style lang="less">
.job-item-modal {
    .modal-footer {
        text-align: center !important;
    }
}
</style>

<template>
<modal class="job-item-modal"
    :class="{
        'modal-success': item.status === 'done',
        'modal-danger': item.status === 'failed',
        'modal-warning': item.status === 'skipped'
    }">
    <div class="modal-body">
        <dl class="clearfix">
            <dt>{{ _('Remote ID') }}</dt>
            <dd>{{ item.remote_id }}</dd>
            <dt>{{ _('Started at') }}</dt>
            <dd>{{ item.started | dt }}</dd>
            <dt>{{ _('Ended at') }}</dt>
            <dd>{{ item.ended | dt }}</dd>
            <dt>{{ _('Status') }}</dt>
            <dd><span class="label label-{{ item.status | statusClass }}">{{ item.status | statusI18n }}</span></dd>
            <dt v-if="item.dataset">{{ _('Dataset') }}</dt>
            <dd v-if="item.dataset">
                <dataset-card class="col-xs-12"
                    v-if="item.dataset.id"
                    :datasetid="item.dataset.id">
                </dataset-card>
                <dataset-card class="col-xs-12"
                    v-if="!item.dataset.id"
                    :dataset="item.dataset">
                </dataset-card>
            </dd>
            <dt v-if="item.errors.length">{{ _('Errors') }}</dt>
            <dd v-if="item.errors.length">
                <div v-for="error in item.errors">
                    {{{error.message | markdown}}}
                    <pre>{{error.details}}</pre>
                </div>
            </dd>
        </dl>
    </div>
    <footer class="modal-footer">
        <button type="button" class="btn btn-outline btn-flat pointer"
            data-dismiss="modal">
            {{ _('Close') }}
        </button>
    </footer>
</modal>
</template>

<script>
import {STATUS_CLASSES, STATUS_I18N} from 'models/harvest/item';

export default {
    name: 'JobItemModal',
    components: {
        'modal': require('components/modal.vue'),
        'dataset-card': require('components/dataset/card.vue')
    },
    props: ['item'],
    data: function() {
        return {};
    },
    filters: {
        statusClass: function(value) {
            return STATUS_CLASSES[value];
        },
        statusI18n: function(value) {
            return STATUS_I18N[value];
        }
    }
};
</script>
