<template>
<layout :title="source.name || ''" :subtitle="_('Edit')">
    <div class="row">
        <div class="col-xs-12">
            <box>
                <harvest-form :source="source"></harvest-form>
            </box>
        </div>
    </div>
    <div class="row">
        <div class="col-xs-12">
            <box :title="_('Filters')">
                <mappings-form :source="source"></mappings-form>
            </box>
        </div>
    </div>
    <div class="row">
        <preview class="col-xs-12" :source="source"></preview>
    </div>
</layout>
</template>

<script>
import HarvestSource from 'models/harvest/source';
import ItemModal from 'components/harvest/item.vue';
import Vue from 'vue';
import Layout from 'components/layout.vue';

export default {
    name: 'HarvesterEditView',
    props: {
        source: {
            type: HarvestSource,
            default() {
                return new HarvestSource();
            }
        }
    },
    components: {
        box: require('components/containers/box.vue'),
        'harvest-form': require('components/harvest/form.vue'),
        'mappings-form': require('components/harvest/mappings-form.vue'),
        preview: require('components/harvest/preview.vue'),
        Layout
    },
    events: {
        'harvest:job:item:selected': function(item) {
            this.$root.$modal(
                {data: {item: item}},
                Vue.extend(ItemModal)
            );
            return true;
        }
    },
    route: {
        data() {
            this.source.fetch(this.$route.params.oid);
        }
    }
};
</script>
