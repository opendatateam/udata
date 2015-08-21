<style lang="less">
.resource-modal {
    a {
        color: white;
    }
}
</style>

<template>
<modal title="{{ resource.title }}" class="resource-modal"
    v-class="modal-danger: confirm, modal-primary: !confirm"
    v-ref="modal">
    <div class="modal-body">
        <div v-show="!edit && !confirm">
            {{{ resource.description | markdown }}}

            <dl class="dl-horizontal dl-wide">
                <dt>{{ _('URL') }}</dt>
                <dd><a href="{{resource.url}}">{{resource.url}}</a></dd>
                <dt v-if="resource.format">{{ _('Format') }}</dt>
                <dd v-if="resource.format">{{ resource.format }}</dd>
                <dt v-if="resource.mime">{{ _('Mime Type') }}</dt>
                <dd v-if="resource.mime">{{ resource.mime }}</dd>
                <dt v-if="resource.size">{{ _('Size') }}</dt>
                <dd v-if="resource.size">{{ resource.size }}</dd>
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

        <resource-form v-if="edit" v-ref="form" dataset="{{dataset}}" resource="{{resource}}"></resource-form>

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
        <button type="button" class="btn btn-outline btn-flat pointer"
            v-show="!edit && !confirm" v-on="click: edit = true">
            {{ _('Edit') }}
        </button>
        <button type="button" class="btn btn-danger btn-sm btn-flat pointer pull-left"
            v-show="!edit && !confirm" v-on="click: confirm = true">
            {{ _('Delete') }}
        </button>
        <button type="button" class="btn btn-danger btn-outline btn-flat pointer"
            v-show="confirm" v-on="click: delete_confirmed">
            {{ _('Confirm') }}
        </button>
        <button v-show="confirm" type="button" class="btn btn-warning btn-sm btn-flat pointer pull-left"
          v-on="click: confirm = false">
            {{ _('Cancel') }}
        </button>
        <button type="button" class="btn btn-outline btn-flat pointer"
            v-show="edit" v-on="click: save">
            {{ _('Save') }}
        </button>
        <button v-show="edit" type="button" class="btn btn-primary btn-sm btn-flat pointer pull-left"
            v-on="click: edit = false">
            {{ _('Cancel') }}
        </button>
    </footer>
</modal>
</template>

<script>
'use strict';

var $ = require('jquery');

module.exports = {
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
            if (this.$.form.validate()) {
                // $.extend(this.resource, this.$.form.serialize());
                // this.dataset.$data = component.$.form.serialize();
                this.dataset.save_resource(this.$.form.serialize());
                this.$.modal.close();
                return true;
            }
        },
        delete_confirmed: function() {
            this.dataset.delete_resource(this.resource.id);
            this.$.modal.close();
        }
    }
};
</script>
