<template>
<form-layout icon="tasks" :title="title" :save="save" :cancel="cancel" footer="true" :model="source">
    <harvest-form v-ref:form :source="source"></harvest-form>
    <!--div class="row" slot="extras">
        <div class="col-xs-12">
            <box :title="_('Filters')">
                <mappings-form :source="source"></mappings-form>
            </box>
        </div>
    </div-->
    <div class="row" slot="extras">
        <preview class="col-xs-12" :source="source"></preview>
    </div>
</form-layout>
</template>

<script>
import Box from 'components/containers/box.vue';
import FormLayout from 'components/form-layout.vue';
import HarvestForm from 'components/harvest/form.vue';
import HarvestSource from 'models/harvest/source';
import ItemModal from 'components/harvest/item.vue';
import Preview from 'components/harvest/preview.vue';

export default {
    data: function() {
        return {
            source: new HarvestSource(),
        };
    },
    components: {Box, FormLayout, HarvestForm, Preview},
    computed: {
        title() {
            if (this.source.name) {
                return this._('Edit harvest source "{name}"', {
                    name: this.source.name
                });
            }
        }
    },
    methods: {
        save() {
            let form = this.$refs.form;
            if (form.validate()) {
                this.source.update(form.serialize(), (response) => {
                    this.source.on_fetched(response);
                    this.$go({name: 'harvester', params: {oid: this.source.id}});
                }, form.on_error);
            }
        },
        cancel() {
            this.$go({name: 'harvester', params: {oid: this.source.id}});
        }
    },
    events: {
        'harvest:job:item:selected': function(item) {
            this.$root.$modal(ItemModal, {item: item});
            return true;
        }
    },
    route: {
        data() {
            this.source.fetch(this.$route.params.oid);
            this.$scrollTo(this.$el);
        }
    }
};
</script>
