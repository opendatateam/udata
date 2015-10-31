<template>
    <box title="OAuth" icon="plug"
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
                <tr v-for="client in clients"
                    v-link="'/oauth/clients/' + client.id + '/'">
                    <td>{{client.name}}</td>
                    <td>{{client.description}}</td>
                    <td>
                        <i class="fa fa-fw fa-{{client.enabled ? 'play' : 'stop'}} text-{{client.enabled ? 'green' : 'red'}}"></i>
                    </td>
                </tr>
            </tbody>
        </table>
    </box>
</template>

<script>
export default {
    name: 'oauth-widget',
    components: {
        box: require('components/containers/box.vue')
    },
    data: function() {
        return {
            title: 'OAuth',
            clients: []
        };
    }
};
</script>
