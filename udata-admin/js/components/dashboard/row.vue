<template>
    <div class="row dashboard-row">
        <div class="col-lg-3 col-xs-6" v-repeat="widget:row">
            {{widget}}
        </div>
    </div>
</template>

<script>
'use strict';

module.exports = {
    name: 'DashboardRow',
    inherit: true,
    props: ['row'],
    data: function() {
        return {
            row: []
        };
    },
    directives: {
        'widget': {}
    }
};
</script>
