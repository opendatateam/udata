<template>
<div>
    <datatable :title="title" icon="tasks"
        boxclass="harvesters-widget"
        :fields="fields" :p="sources" :loading="sources.loading"
        :empty="_('No harvester')">
    </datatable>
</div>
</template>

<script>
import {Model} from 'models/base';
import HarvestSources from 'models/harvest/sources';
import {VALIDATION_STATUS_I18N, VALIDATION_STATUS_CLASSES} from 'models/harvest/source';
import {STATUS_CLASSES, STATUS_I18N} from 'models/harvest/job';
import Datatable from 'components/datatable/widget.vue';
import placeholders from 'helpers/placeholders';

const MASK = ['id', 'name', 'owner', 'last_job{status,ended}', 'organization{name,logo_thumbnail}', 'backend', 'validation{state}', 'deleted'];

export default {
    MASK,
    components: {Datatable},
    props: {
        owner: {
            type: Model,
            default: () => {id: null}
        }
    },
    data() {
        return {
            title: this._('Harvesters'),
            sources: new HarvestSources({mask: MASK, query: {deleted: true}}),
        };
    },
    computed: {
        fields() {
            const fields = [];
            // Only display owner if not filtered
            if (!(this.owner instanceof Model)) {
                fields.push({
                    key(item) {
                        if (item.organization) {
                            return placeholders.org_logo(item.organization, 30);
                        } else {
                            return placeholders.user_avatar(item.owner, 30);
                        }
                    },
                    type: 'thumbnail',
                    width: 30,
                });
            }
            fields.push({
                label: this._('Name'),
                key: 'name',
                align: 'left',
                type: 'deletable-text'
            });
            // Only display owner if not filtered
            if (!(this.owner instanceof Model)) {
                fields.push({
                    label: this._('Owner'),
                    key(item) {
                        if (item.organization) {
                            return item.organization.name;
                        } else {
                            return `${item.owner.first_name} ${item.owner.last_name}`;
                        }
                    },
                    align: 'left',
                    type: 'text',
                    width: 250
                });
            }
            fields.push({
                label: this._('Backend'),
                key: 'backend',
                align: 'left',
                type: 'text',
                width: 100
            }, {
                label: this._('Status'),
                key(item) {
                    if (item.deleted) {
                        return 'deleted';
                    } else if (item.validation.state == 'pending') {
                        return 'validation';
                    } else if (item.validation.state == 'refused') {
                        return 'refused';
                    } else {
                        return item.last_job.status;
                    }
                },
                type: 'label',
                width: 100,
                label_type(status) {
                    if (!status) return 'default';
                    else if (status == 'validation') return 'default';
                    else if (status == 'refused') return 'danger';
                    else return STATUS_CLASSES[status];
                },
                label_func: (status) => {
                    if (!status) return this._('No job yet');
                    else if (status == 'validation') return this._('Validation');
                    else if (status == 'refused') return this._('Refused');
                    return STATUS_I18N[status];
                }
            }, {
                label: this._('Last run'),
                key: 'last_job.ended',
                align: 'left',
                type: 'timeago',
                width: 120
            });
            return fields;
        }
    },
    events: {
        'datatable:item:click': function(harvester) {
            this.$go({name: 'harvester', params: {oid: harvester.id}});
        }
    },
    ready() {
        if (this.owner instanceof Model) {
            // Only fetch if binding occured and object is already fetched, else wait for watch
            if (this.owner.id) {
                this.sources.fetch({owner: this.owner.id});
            }
        } else {
            this.sources.fetch();
        }
    },
    watch: {
        'owner.id': function(ownerid) {
            if (ownerid) {
                this.sources.fetch({owner: ownerid});
            }
        }
    }
};
</script>
