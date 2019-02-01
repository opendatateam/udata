<template>
<div>
    <modal v-ref:modal :title="_('Scheduling')" class="schedule-modal" :class="modalClass">
        <div class="modal-body" v-if="!unscheduling">
            <horizontal-form class="schedule-form" :fields="fields" :defs="defs" v-ref:form
                :model="source">
            </horizontal-form>
        </div>
        <div class="modal-body" v-else>
            <p class="lead text-center">
                {{ _('You are about to unschedule this harvest source') }}
            </p>
            <p class="lead text-center">
                {{ _('Are you sure?') }}
            </p>
        </div>
        <footer class="modal-footer text-center">
            <button type="button" class="btn btn-flat pull-left" :class="cancelClass" @click="cancel">
                {{ _('Cancel') }}
            </button>
            <button type="button"  v-if="!unscheduling && source.schedule"
                class="btn btn-danger btn-flat" @click="unscheduling = true">
                {{ _('Unschedule') }}
            </button>
            <button type="button" v-if="!unscheduling" class="btn btn-outline btn-flat" @click="schedule">
                {{ _('Schedule') }}
            </button>
            <button type="button" v-if="unscheduling" class="btn btn-warning btn-flat" @click="unschedule">
                {{ _('Confirm') }}
            </button>
        </footer>
    </modal>
</div>
</template>
<script>
import API from 'api';

import HorizontalForm from 'components/form/horizontal-form.vue';

import HarvestSource from 'models/harvest/source';

import Modal from 'components/modal.vue'

const MASK = ['id', 'name', 'schedule'];
const DEFAULT_SCHEDULE = '0 0 * * *';
const CRON_DOC_URL = 'https://crontab.guru/';

export default {
    name: 'schedule-modal',
    components: {Modal, HorizontalForm},
    computed: {
        modalClass() {
            return [this.unscheduling ? 'modal-danger' : 'modal-primary'];
        },
        cancelClass() {
            return [this.unscheduling ? 'btn-danger' : 'btn-primary'];
        }
    },
    data() {
        return {
            source: new HarvestSource({mask: MASK}),
            unscheduling: false,
            fields: [{
                id: 'schedule',
                label: this._('Scheduling'),
            }],
            defs: {
                properties: {
                    schedule: {
                        type: 'string',
                        default: DEFAULT_SCHEDULE,
                        description: this._('This is a cron expressions. See {url} for more details.', {
                            url: CRON_DOC_URL
                        })
                    }
                },
                required: ['cron']
            }
        };
    },
    events: {
        'modal:closed': function() {
            this.goBack();
        }
    },
    route: {
        data() {
            if (this.$route.params.oid !== this.source.id) {
                this.source.fetch(this.$route.params.oid);
            }
        }
    },
    methods: {
        schedule() {
            if (this.$refs.form.validate()) {
                const params = {
                    ident: this.$route.params.oid,
                    payload: this.$refs.form.serialize().schedule
                }
                API.harvest.schedule_harvest_source(params, (response) => {
                    const msg = this._('{name} has been scheduled on {schedule}', {
                        name: response.obj.name,
                        schedule: response.obj.schedule
                    });
                    this.$dispatch('notify', {title: msg, autoclose: true});
                    this.goBack();
                }, this.$root.handleApiError);
            }
        },
        unschedule() {
            API.harvest.unschedule_harvest_source({ident: this.$route.params.oid},  (source) => {
                const msg = this._('{name} has been unscheduled', {
                    name: this.source.name,
                });
                this.$dispatch('notify', {title: msg, autoclose: true});
                this.goBack();
            }, this.$root.handleApiError);
        },
        cancel() {
            if (this.unscheduling) {
                this.unscheduling = false;
            } else {
                this.goBack();
            }
        },
        goBack() {
            this.$refs.modal.close();
            this.$go({name: 'harvester', params: {oid: this.$route.params.oid}});
        }
    }
};
</script>
<style lang="less"></style>
