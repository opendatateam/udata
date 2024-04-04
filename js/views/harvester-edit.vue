<template>
<div>
<form-layout icon="tasks" :title="title" :save="save" :cancel="cancel" footer="true" :model="source">
    <harvest-form v-ref:form :source="source"></harvest-form>
    <div v-if="previewSource" class="row" slot="extras">
        <preview class="col-xs-12" :source="previewSource" from-config></preview>
    </div>
</form-layout>
</div>
</template>

<script>
import Box from 'components/containers/box.vue';
import FormLayout from 'components/form-layout.vue';
import HarvestForm from 'components/harvest/form.vue';
import HarvestSource from 'models/harvest/source';
import ItemModal from 'components/harvest/item.vue';
import Preview from 'components/harvest/preview.vue';

const MASK = [
    'id',
    'name',
    'url',
    'description',
    'owner',
    'last_job{status,ended}',
    'organization',
    'backend',
    'validation{state}',
    'config',
    'active',
    'autoarchive',
];

export default {
    name: 'harvester-edit',
    data() {
        return {
            source: new HarvestSource({mask: MASK}),
            previewSource: undefined,
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
    ready() {
        this.source.$on('updated', () => {
            this.$nextTick(() => {
                this.previewSource = Object.assign(new HarvestSource(), this.$refs.form.serialize());
            });
        });
    },
    methods: {
        save() {
            const form = this.$refs.form;
            if (form.validate()) {
                this.source.update(form.serialize(), form.on_error);
            }
        },
        on_success() {
            this.$dispatch('notify', {
                autoclose: true,
                title: this._('Changes saved'),
                details: this._('The harvester has been updated.')
            });
            this.$go({name: 'harvester', params: {oid: this.source.id}});
        },
        cancel() {
            this.$go({name: 'harvester', params: {oid: this.source.id}});
        }
    },
    events: {
        'harvest:job:item:selected': function(item) {
            this.$root.$modal(ItemModal, {item: item});
            return true;
        },
        'harvest:source:form:changed': function(data) {
            this.previewSource = Object.assign(new HarvestSource(), data);
        }
    },
    route: {
        data() {
            this.$scrollTo(this.$el);
            this.source.fetch(this.$route.params.oid);
            this.source.$once('updated', () => {
                this.updHandler = this.source.$once('updated', this.on_success);
            });
        },
        deactivate() {
            if (this.updHandler) {
                this.updHandler.remove();
                this.updHandler = undefined;
            }
        }
    }
};
</script>
