<template>
    <box :title="title" icon="cubes"
        boxclass="box-solid reused-datasets-widget"
        footerClass="text-center">
        <div class="row">
            <card class="col-md-6"
                v-for="id in reuse.datasets | ids" :datasetid="id"
            ></card>

        </div>
        <footer slot="footer">
            <a class="uppercase">{{ _('Add') }}</a>
        </footer>
    </box>
</template>

<script>
export default {
    name: 'datasets-list',
    components: {
        box: require('components/containers/box.vue'),
        card: require('components/dataset/card.vue')
    },
    data: function() {
        return {
            title: this._('Reused datasets')
        };
    },
    props: ['reuse'],
    filters: {
        ids: function(list) {
            return list ? list.map(function(item) {
                return item.id;
            }) : [];
        }
    }
};
</script>
