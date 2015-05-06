<template>
    <box-container title="{{ title }}" icon="tasks"
        boxclass="box-solid harvesters-widget"
        bodyclass="table-responsive no-padding">
        <aside>
            <div class="box-search">
                <div class="input-group">
                    <input type="text" class="form-control input-sm pull-right" style="width: 150px;" placeholder="{{'Search'|i18n}}">
                    <div class="input-group-btn">
                        <button class="btn btn-sm btn-flat">
                            <i class="fa fa-search"></i>
                        </button>
                    </div>
                </div>
            </div>
        </aside>
        <table class="table table-hover">
            <thead>
                <tr>
                    <th v-i18n="Name"></th>
                    <th v-i18n="Description"></th>
                    <th width="20px"></th>
                </tr>
            </thead>
            <tbody>
                <tr v-repeat="sources" v-route="/harvester/{{id}}/">
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

var Vue = require('vue');

module.exports = {
    name: 'harvesters-widget',
    components: {
        'box-container': require('components/containers/box.vue')
    },
    data: function() {
        return {
            title: Vue._('Harvesters'),
            sources: require('models/harvest/sources').items
        };
    }
};
</script>
