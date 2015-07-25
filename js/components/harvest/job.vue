<style lang="less"></style>

<template>
<box icon="cog" class="box-solid" footer="{{toggled}}"
    loading="{{job.loading}}">
    <dl>
        <dt>ID</dt>
        <dd>{{ job.id }}</dd>
        <dt>{{ _('Created at') }}</dt>
        <dd>{{ job.created }}</dd>
        <dt>{{ _('Started at') }}</dt>
        <dd>{{ job.started }}</dd>
        <dt>{{ _('Ended at') }}</dt>
        <dd>{{ job.ended }}</dd>
        <dt>{{ _('Status') }}</dt>
        <dd>{{ job.status }}</dd>
    </dl>
    <ul>
        <li v-repeat="error:job.errors">
            <p>{{error.created_at}}</p>
            <p>{{error.message}}</p>
            <p>{{error.details}}</p>
        </li>
    </ul>
</box>
</template>

<script>
import HarvestJob from 'models/harvest/job';

export default {
    name: 'JobDetails',
    props: ['job'],
    components: {
        'box': require('components/containers/box.vue'),
    },
    data: function() {
        return {
            job: new HarvestJob()
        };
    }
};
</script>
