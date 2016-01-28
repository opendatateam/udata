<template>
<layout :title="_('System')">
    <div class="row">
        <harvesters-widget class="col-xs-12 col-md-6"></harvesters-widget>
        <jobs-widget class="col-xs-12 col-md-6"></jobs-widget>
        <oauth-widget class="col-xs-12 col-md-6"></oauth-widget>
    </div>
</oauth-widget>
</template>

<script>
import Layout from 'components/layout.vue';

export default {
    name: 'SystemView',
    components: {
        'harvesters-widget': require('components/harvest/sources.vue'),
        'jobs-widget': require('components/system/jobs.vue'),
        'oauth-widget': require('components/system/oauth.vue'),
        Layout
    }
};
</script>
