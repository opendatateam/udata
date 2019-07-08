<template>
<div>
<layout :title="source.name || ''" :subtitle="source.backend || ''" :actions="actions" :badges="badges" >
    <div class="alert alert-info" v-if="should_validate">
        <div class="btn-toolbar pull-right">
            <div class="btn-group">
                <button class="btn btn-danger btn-xs" @click="confirm_delete">{{ _('Delete') }}</button>
            </div>
            <div class="btn-group">
                <button class="btn btn-primary btn-xs" @click="validate_source">{{ _('Validate') }}</button>
            </div>
        </div>
        {{ _('This harvest source has not been validated') }}
    </div>
    <div class="alert alert-warning" v-if="display_warning">
        {{ _('This harvest source has not been validated') }}
    </div>
    <div class="row">
        <source-widget :source="source"
            :class="{
                'col-xs-12': !current_job,
                'col-md-4': current_job,
            }">
        </source-widget>
        <job-widget
            v-if="current_job"
            :job="current_job"
            class="col-md-8">
        </job-widget>
    </div>
    <div class="row" v-if="should_validate">
        <preview class="col-xs-12" :source="source"></preview>
    </div>
</layout>
</div>
</template>

<script>
import HarvestSource from 'models/harvest/source';
import HarvestJob from 'models/harvest/job';
import ItemModal from 'components/harvest/item.vue';
import Vue from 'vue';
import Preview from 'components/harvest/preview.vue';
import SourceWidget from 'components/harvest/source.vue';
import JobWidget from 'components/harvest/job.vue';
import Layout from 'components/layout.vue';

const MASK = ['id', 'name', 'url', 'owner', 'organization', 'backend', 'validation{state}', 'schedule', 'deleted'];

export default {
    name: 'HarvestSourceView',
    components: {Preview, SourceWidget, JobWidget, Layout},
    data() {
        return {
            source: new HarvestSource({mask: MASK}),
            current_job: null,
            current_item: null,
        };
    },
    computed: {
        is_validation_pending() {
            return this.source && this.source.validation
                && this.source.validation.state === 'pending';
        },
        should_validate() {
            return this.is_validation_pending && this.$root.me.is_admin;
        },
        display_warning() {
            return this.is_validation_pending && !this.$root.me.is_admin;
        },
        badges() {
            if (this.source && this.source.deleted) {
                return [{
                    class: 'danger',
                    label: this._('Deleted')
                }];
            } else {
                return [];
            }
        },
        actions() {
            const actions = [{
                label: this._('Edit'),
                icon: 'pencil',
                method: this.edit
            }];
            if (this.$root.me.is_admin) {
                actions.push({
                    label: this._('Scheduling'),
                    icon: 'history',
                    method: this.schedule
                }, {divider: true});
            }
            actions.push({
                label: this._('Delete'),
                icon: 'trash',
                method: this.confirm_delete
            });
            return actions;
        }
    },
    events: {
        'harvest:job:selected': function(job) {
            this.current_job = new HarvestJob({data: job}).fetch();
            return true;
        },
        'harvest:job:item:selected': function(item) {
            this.current_item = item;
            this.$root.$modal(ItemModal, {item: item});
            return true;
        }
    },
    methods: {
        edit() {
            this.$go({name: 'harvester-edit', params: {oid: this.source.id}});
        },
        confirm_delete() {
            this.$root.$modal(
                require('components/harvest/delete-modal.vue'),
                {source: this.source}
            );
        },
        validate_source() {
            this.$root.$modal(
                require('components/harvest/validation-modal.vue'),
                {source: this.source}
            );
        },
        schedule() {
            this.$go({name: 'harvester-schedule', params: {oid: this.source.id}});
        }
    },
    route: {
        data() {
            this.source.fetch(this.$route.params.oid);
        }
    }
};
</script>
