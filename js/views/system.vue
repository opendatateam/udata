<template>
    <div class="row">
        <harvesters-widget class="col-xs-12 col-md-6"></harvesters-widget>
        <jobs-widget class="col-xs-12 col-md-6"></jobs-widget>
        <oauth-widget class="col-xs-12 col-md-6" />
    </div>
</template>

<script>
export default {
    name: 'SystemView',
    components: {
        'harvesters-widget': require('components/harvest/sources.vue'),
        'jobs-widget': require('components/system/jobs.vue'),
        'oauth-widget': require('components/system/oauth.vue')
    },
    data: function() {
        return {
            meta: {
                title: this._('System')
            }
        };
    }
};
</script>
