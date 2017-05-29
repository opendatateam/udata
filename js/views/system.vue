<template>
<div>
<layout :title="_('System')">
    <div class="row">
        <harvesters-widget class="col-xs-12"></harvesters-widget>
        <jobs-widget class="col-xs-12 col-md-6"></jobs-widget>
        <oauth-widget class="col-xs-12 col-md-6"></oauth-widget>
    </div>
</layout>
</div>
</template>

<script>
import Layout from 'components/layout.vue';
import HarvestersWidget from 'components/harvest/sources.vue';
import JobsWidget from 'components/system/jobs.vue';
import OauthWidget from 'components/system/oauth.vue';

export default {
    name: 'SystemView',
    components: {HarvestersWidget, JobsWidget, OauthWidget, Layout}
};
</script>
