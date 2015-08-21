<template>
    <box-container title="OAuth" icon="plug"
        boxclass="box-info"
        bodyclass="table-responsive no-padding">
        <table class="table table-hover">
            <thead>
                <tr>
                    <th v-i18n="Name"></th>
                    <th v-i18n="Description"></th>
                    <th width="20px"></th>
                </tr>
            </thead>
            <tbody>
                <tr v-repeat="clients" v-route="/oauth/clients/{{id}}/">
                    <td>{{name}}</td>
                    <td>{{description}}</td>
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
    name: 'oauth-widget',
    components: {
        'box-container': require('components/containers/box.vue')
    },
    data: function() {
        return {
            title: 'OAuth',
            clients: []
        };
    }
};
</script>
