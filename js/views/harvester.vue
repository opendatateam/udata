<template>
    <div class="alert alert-info" v-if="should_validate">
        <button class="pull-right btn btn-primary btn-xs"
            @click="validate_source">{{ _('Validate') }}</button>
        {{ _('This harvest source has not been validated') }}
    </div>
    <div class="alert alert-warning" v-if="display_warning">
        {{ _('This harvest source has not been validated') }}
    </div>
    <div class="row">
        <source-widget source="{{source}}"
            v-class="
                col-xs-12: !current_job,
                col-md-4: current_job,
            ">
        </source-widget>
        <job-widget
            v-if="current_job"
            job="{{current_job}}"
            class="col-md-8">
        </job-widget>
    </div>
    <div class="row" v-if="should_validate">
        <preview class="col-xs-12" source="{{source}}"></preview>
    </div>
</template>

<script>
import HarvestSource from 'models/harvest/source';
import ItemModal from 'components/harvest/item.vue';
import Vue from 'vue';

export default {
    name: 'HarvestSourceView',
    data: function() {
        return {
            source_id: null,
            source: new HarvestSource(),
            current_job: null,
            current_item: null,
            meta: {
                title: null,
                subtitle: null,
                actions: [{
                    label: this._('Edit'),
                    icon: 'pencil',
                    method: 'edit'
                },{
                    label: this._('Delete'),
                    icon: 'trash',
                    method: 'confirm_delete'
                }]
            }
        };
    },
    computed: {
        is_validation_pending: function() {
            return this.source && this.source.validation
                && this.source.validation.state === 'pending';
        },
        should_validate: function() {
            return this.is_validation_pending && this.$root.me.is_admin;
        },
        display_warning: function() {
            return this.is_validation_pending && !this.$root.me.is_admin;
        }
    },
    events: {
        'harvest:job:selected': function(job) {
            this.current_job = job;
        },
        'harvest:job:item:selected': function(item) {
            this.current_item = item;
            this.$root.$modal(
                {data: {item: item}},
                Vue.extend(ItemModal)
            );
        }
    },
    methods: {
        edit: function() {
            this.$go('/harvester/' + this.source.id + '/edit');
        },
        confirm_delete: function() {
            this.$root.$modal(
                {data: {source: this.source}},
                Vue.extend(require('components/harvest/delete-modal.vue'))
            );
        },
        validate_source: function() {
            this.$root.$modal(
                {data: {source: this.source}},
                Vue.extend(require('components/harvest/validation-modal.vue'))
            );
        }
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
        },
        'source.backend': function(backend) {
            if (backend) {
                this.meta.subtitle = backend;
                this.$dispatch('meta:updated', this.meta);
            }
        }
    },
    components: {
        preview: require('components/harvest/preview.vue'),
        'source-widget': require('components/harvest/source.vue'),
        'job-widget': require('components/harvest/job.vue'),
    }
};
</script>
