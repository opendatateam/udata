<style lang="less">
.resource-modal {
    dd {
        a {
            color: white;
            text-decoration: underline;
        }
    }

    .dl-wide dd {
        // URLs and hashes are not breakable on words
        word-break: break-all;
    }
}
</style>

<template>
<div>
<modal :title="resource.title" class="resource-modal" :large="edit"
    :class="{ 'modal-danger': confirm, 'modal-primary': !confirm }"
    v-ref:modal>
    <div class="modal-body">
        <div v-show="!edit && !confirm">
            {{{ resource.description | markdown }}}

            <dl class="dl-horizontal dl-wide">
                <dt>{{ _('Type') }}</dt>
                <dd>{{ resource | resource_type_label }}</dd>
                <dt>{{ _('Location') }}</dt>
                <dd v-if="resource.filetype == 'file'">
                    {{ _('This resource is hosted on our servers') }}
                </dd>
                <dd v-if="resource.filetype == 'remote'">
                    {{ _('This resource is hosted on an external server') }}
                </dd>
                <dt>{{ _('URL') }}</dt>
                <dd><a :href="resource.url">{{resource.url}}</a></dd>
                <dt v-if="resource.format">{{ _('Format') }}</dt>
                <dd v-if="resource.format">{{ resource.format }}</dd>
                <dt v-if="resource.mime">{{ _('Mime Type') }}</dt>
                <dd v-if="resource.mime">{{ resource.mime }}</dd>
                <dt v-if="resource.filesize">{{ _('Size') }}</dt>
                <dd v-if="resource.filesize">{{ resource.filesize }}</dd>
                <dt v-if="resource.checksum">{{ resource.checksum.type }}</dt>
                <dd v-if="resource.checksum">{{ resource.checksum.value }}</dd>
                <dt v-if="resource.created_at">{{ _('Created on') }}</dt>
                <dd v-if="resource.created_at">{{ resource.created_at | dt }}</dd>
                <dt v-if="resource.last_modified">{{ _('Modified on') }}</dt>
                <dd v-if="resource.last_modified">{{ resource.last_modified | dt }}</dd>
                <dt v-if="resource.published">{{ _('Published on') }}</dt>
                <dd v-if="resource.published">{{ resource.published | dt }}</dd>
                <dt v-if="resource.metrics && resource.metrics.downloads">{{ _('Downloads') }}</dt>
                <dd v-if="resource.metrics && resource.metrics.downloads">{{ resource.metrics.downloads }}</dd>
                <dt v-if="is_community">{{ _('Publish by') }}</dt>
                <dd v-if="is_community">
                    <user-card v-if="resource.owner" :user="resource.owner"></user-card>
                    <org-card v-if="resource.organization" :organization="resource.organization"></org-card>
                </dd>
            </dl>
        </div>

        <resource-form v-if="edit" v-ref:form :dataset="dataset" :resource="resource" :hide-notifications="false"></resource-form>

        <div v-show="confirm">
            <p class="lead text-center">
                {{ _('You are about to delete this resource') }}
            </p>
            <p class="lead text-center">
                {{ _('Are you sure ?') }}
            </p>
        </div>
    </div>

    <footer class="modal-footer text-center">
        <button type="button" v-show="!edit && !confirm"
                class="btn btn-primary btn-sm btn-flat pull-left"
                @click="$refs.modal.close">
            {{ _('Close') }}
        </button>
        <button type="button" v-show="confirm"
                class="btn btn-warning btn-sm btn-flat pull-left"
                @click="confirm = false">
            {{ _('Cancel') }}
        </button>
        <button type="button" v-show="edit"
                class="btn btn-primary btn-sm btn-flat pull-left"
                @click="edit = false">
            {{ _('Cancel') }}
        </button>
        <button type="button" v-show="!edit && !confirm && can_edit"
                class="btn btn-danger btn-xs btn-flat"
                @click="confirm = true">
            {{ _('Delete') }}
        </button>
        <button type="button" v-show="!edit && !confirm && can_edit"
                class="btn btn-outline btn-flat"
                @click="edit = true">
            {{ _('Edit') }}
        </button>
        <button type="button" v-show="confirm"
                class="btn btn-danger btn-outline btn-flat"
                @click="delete_confirmed">
            {{ _('Confirm') }}
        </button>
        <button type="button" v-show="edit"
                class="btn btn-outline btn-flat"
                @click="save">
            {{ _('Save') }}
        </button>
    </footer>
</modal>
</div>
</template>

<script>
import API from 'api';
import Dataset from 'models/dataset';
import Resource from 'models/resource';
import CommunityResource from 'models/communityresource';

import Modal from 'components/modal.vue'
import ResourceForm from 'components/dataset/resource/form.vue'
import OrgCard from 'components/organization/card.vue'
import UserCard from 'components/user/card.vue'
import DatasetFilters from 'components/dataset/filters';

export default {
    name: 'resource-modal',
    components: {Modal, ResourceForm, OrgCard, UserCard},
    mixins: [DatasetFilters],
    data() {
        return {
            edit: false,
            confirm: false,
            dataset: this.$parent.$parent.dataset,
            resource: new Resource(),
            next_route: null
        };
    },
    computed: {
        can_edit() {
            if (this.is_community) {
                return this.$root.me.can_edit(this.resource);
            } else {
                return this.$root.me.can_edit(this.dataset);
            }
        },
        is_community() {
            return this.resource instanceof CommunityResource
        }
    },
    events: {
        'modal:closed': function() {
            if (this.next_route) {
                this.$go(this.next_route);
            }
        }
    },
    route: {
        data() {
            if (this.$route.matched.length > 1) {
                // This is a nested view
                let idx = this.$route.matched.length - 2,
                    parent = this.$route.matched[idx];
                this.next_route = {
                    name: parent.handler.name,
                    params: parent.params
                };
            }
            if (this.$route.name.includes('community')) {
                this.resource = new CommunityResource();
                this.resource.fetch(this.$route.params.rid);
            } else {
                this.resource.fetch(this.$route.params.oid, this.$route.params.rid);
            }
        }
    },
    methods: {
        save() {
            if (this.$refs.form.validate()) {
                if (this.is_community) {
                    Object.assign(this.resource, this.$refs.form.serialize());
                    this.resource.save();
                } else {
                    this.dataset.save_resource(this.$refs.form.serialize());
                }
                this.$refs.modal.close();
                return true;
            }
        },
        delete_confirmed() {
            if (this.is_community) {
                API.datasets.delete_community_resource({community: this.resource.id},
                    (response) => {
                        this.$refs.modal.close();
                    }
                );
            } else {
                this.dataset.delete_resource(this.resource.id);
                this.$refs.modal.close();
            }
        }
    },
    watch: {
        'dataset.resources': function(resources) {
            if (!this.is_community) {
                resources.some((resource) => {
                    if (resource.id === this.$route.params.rid) {
                        this.resource = new Resource({data: resource});
                        return true;
                    }
                });
            }
        }
    }
};
</script>
