<style lang="less">
.resource-modal {
    a {
        color: white;
    }
}
</style>

<template>
<modal title="{{ resource.title }}" class="resource-modal"
    :class="{ 'modal-danger': confirm, 'modal-primary': !confirm }"
    v-ref:modal>
    <div class="modal-body">
        <div v-show="!edit && !confirm">
            {{{ resource.description | markdown }}}

            <dl class="dl-horizontal dl-wide">
                <dt>{{ _('Type') }}</dt>
                <dd v-if="resource.filetype == 'file'">
                    {{ _('This resource is hosted on our servers') }}
                </dd>
                <dd v-if="resource.filetype == 'remote'">
                    {{ _('This resource is hosted on an external server') }}
                </dd>
                <dd v-if="resource.filetype == 'api'">
                    {{ _('This resource is an API') }}
                </dd>
                <dt>{{ _('URL') }}</dt>
                <dd><a href="{{resource.url}}">{{resource.url}}</a></dd>
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
                <dt v-if="resource.metrics.downloads">{{ _('Downloads') }}</dt>
                <dd v-if="resource.metrics.downloads">{{ resource.metrics.downloads }}</dd>
            </dl>
        </div>

        <resource-form v-if="edit" v-ref:form dataset="{{dataset}}" resource="{{resource}}"></resource-form>

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
                class="btn btn-primary btn-sm btn-flat pointer pull-left"
                data-dismiss="modal">
            {{ _('Close') }}
        </button>
        <button type="button" v-show="confirm"
                class="btn btn-warning btn-sm btn-flat pointer pull-left"
                @click="confirm = false">
            {{ _('Cancel') }}
        </button>
        <button type="button" v-show="edit"
                class="btn btn-primary btn-sm btn-flat pointer pull-left"
                @click="edit = false">
            {{ _('Cancel') }}
        </button>
        <button type="button" v-show="!edit && !confirm"
                class="btn btn-danger btn-xs btn-flat pointer"
                @click="confirm = true">
            {{ _('Delete') }}
        </button>
        <button type="button" v-show="!edit && !confirm"
                class="btn btn-outline btn-flat pointer"
                @click="edit = true">
            {{ _('Edit') }}
        </button>
        <button type="button" v-show="confirm"
                class="btn btn-danger btn-outline btn-flat pointer"
                @click="delete_confirmed">
            {{ _('Confirm') }}
        </button>
        <button type="button" v-show="edit"
                class="btn btn-outline btn-flat pointer"
                @click="save">
            {{ _('Save') }}
        </button>
    </footer>
</modal>
</template>

<script>
export default {
    components: {
        'modal': require('components/modal.vue'),
        'resource-form': require('components/dataset/resource/form.vue')
    },
    data: function() {
        return {
            edit: false,
            confirm: false,
            dataset: {}
        };
    },
    methods: {
        save: function() {
            if (this.$refs.form.validate()) {
                this.dataset.save_resource(this.$refs.form.serialize());
                this.$refs.modal.close();
                return true;
            }
        },
        delete_confirmed: function() {
            this.dataset.delete_resource(this.resource.id);
            this.$refs.modal.close();
        }
    }
};
</script>
