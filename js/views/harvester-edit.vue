<template>
<box class="col-xs-12">
    <harvest-form source="{{source}}"></harvest-form>
</box>
<box class="col-xs-12">
    <mappings-form source="{{source}}"></mappings-form>
</box>
</template>

<script>
import HarvestSource from 'models/harvest/source';

export default {
    name: 'HarvesterEditView',
    props: ['source'],
    data: function() {
        return {
            source: new HarvestSource(),
            source_id: null,
            meta: {
                title: null,
                subtitle: this._('Edit')
            }
        };
    },
    components: {
        'box': require('components/containers/box.vue'),
        'harvest-form': require('components/harvest/form.vue'),
        'mappings-form': require('components/harvest/mappings-form.vue'),
    },
    watch: {
        source_id: function(id) {
            if (id) {
                this.source.fetch(id);
            }
        },
        'source.name': function(name) {
            if (name) {
                this.meta.title = name;
                this.$dispatch('meta:updated', this.meta);
            }
        }
    }
};
</script>
