<template>
    <box-container title="Jobs" icon="cogs" bodyclass="table-responsive no-padding">
        <table class="table table-hover">
            <thead>
                <tr>
                    <th width="20px" class="text-center"></th>
                    <th v-i18n="Name"></th>
                    <th v-i18n="Schedule"></th>
                    <th width="20px"></th>
                </tr>
            </thead>
            <tbody>
                <tr v-repeat="jobs">
                    <td class="text-center">
                        <span v-class="
                            crontab: fa-clock-o,
                            interval: fa-history
                            " class="fa fa-fw fa-{{crontab ? 'clock-o' : 'history'}}"></span>
                    </td>
                    <td>{{name}}</td>
                    <td>{{schedule}}</td>
                    <td>
                        <i class="fa fa-fw fa-{{enabled ? 'play' : 'stop'}} text-{{enabled ? 'green' : 'red'}}"></i>
                    </td>
                </tr>
            </tbody>
        </table>
    </box-container>
</template>

<script>
'use strict';

module.exports = {
    name: 'jobs-widget',
    components: {
        'box-container': require('components/containers/box.vue')
    },
    data: function() {
        return {
            meta: {
                title: 'Jobs'
            },
            jobs: require('models/jobs').items
        };
    }
};
</script>
