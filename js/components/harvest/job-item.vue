<style lang="less"></style>

<template>
<box>
    <dl>
        <dt>{{ _('Remote ID') }}</dt>
        <dd>{{ item.remote_id }}</dd>
        <dt>{{ _('Started at') }}</dt>
        <dd>{{ item.started | datetime }}</dd>
        <dt>{{ _('Ended at') }}</dt>
        <dd>{{ item.ended | datetime }}</dd>
        <dt>{{ _('Status') }}</dt>
        <dd>{{ item.status }}</dd>
        <dt v-if="item.dataset">{{ _('Dataset') }}</dt>
        <dd v-if="item.dataset">
            <dataset-card class="col-xs-12"
                datasetid="{{item.dataset.id}}">
            </dataset-card>
        </dd>
        <dt v-if="item.errors.length">{{ _('Errors') }}</dt>
        <dd v-if="item.errors.length">
            <div v-repeat="error:item.errors">
                <p><strong>{{error.message}}</strong></p>
                <div>
                <code><pre>{{error.details}}</pre></code>
                </div>
            </div>
        </dd>
    </dl>
</box>
</template>

<script>

export default {
    name: 'JobItemView',
    components: {
        'box': require('components/containers/box.vue'),
        'dataset-card': require('components/dataset/card.vue')
    },
    props: ['item'],
    data: function() {
        return {};
    }
};
</script>
