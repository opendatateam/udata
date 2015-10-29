<style lang="less">
.community-modal {
    a {
        color: white;
    }
}
</style>

<template>
<modal title="{{ community.title }}" class="community-modal"
    v-class="modal-danger: confirm, modal-primary: !confirm"
    v-ref="modal">
    <div class="modal-body">
        <div v-show="!edit && !confirm">
            {{{ community.description | markdown }}}

            <dl class="dl-horizontal dl-wide">
                <dt>{{ _('URL') }}</dt>
                <dd><a href="{{community.url}}">{{community.url}}</a></dd>
                <dt v-if="community.format">{{ _('Format') }}</dt>
                <dd v-if="community.format">{{ community.format }}</dd>
                <dt v-if="community.mime">{{ _('Mime Type') }}</dt>
                <dd v-if="community.mime">{{ community.mime }}</dd>
                <dt v-if="community.size">{{ _('Size') }}</dt>
                <dd v-if="community.size">{{ community.size }}</dd>
                <dt v-if="community.checksum">{{ community.checksum.type }}</dt>
                <dd v-if="community.checksum">{{ community.checksum.value }}</dd>
                <dt v-if="community.created_at">{{ _('Created on') }}</dt>
                <dd v-if="community.created_at">{{ community.created_at | dt }}</dd>
                <dt v-if="community.last_modified">{{ _('Modified on') }}</dt>
                <dd v-if="community.last_modified">{{ community.last_modified | dt }}</dd>
                <dt v-if="community.published">{{ _('Published on') }}</dt>
                <dd v-if="community.published">{{ community.published | dt }}</dd>
            </dl>
        </div>

        <community-form v-if="edit" v-ref="form" resource="{{community}}" dataset="{{resource.dataset}}" community="{{true}}"></community-form>

        <div v-show="confirm">
            <p class="lead text-center">
                {{ _('You are about to delete this community resource') }}
            </p>
            <p class="lead text-center">
                {{ _('Are you sure ?') }}
            </p>
        </div>
    </div>

    <footer class="modal-footer text-center">
        <button type="button" class="btn btn-outline btn-flat pointer"
            v-show="!edit && !confirm" @click="edit = true">
            {{ _('Edit') }}
        </button>
        <button type="button" class="btn btn-danger btn-sm btn-flat pointer pull-left"
            v-show="!edit && !confirm" @click="confirm = true">
            {{ _('Delete') }}
        </button>
        <button type="button" class="btn btn-danger btn-outline btn-flat pointer"
            v-show="confirm" @click="delete_confirmed">
            {{ _('Confirm') }}
        </button>
        <button v-show="confirm" type="button" class="btn btn-warning btn-sm btn-flat pointer pull-left"
          @click="confirm = false">
            {{ _('Cancel') }}
        </button>
        <button type="button" class="btn btn-outline btn-flat pointer"
            v-show="edit" @click="save">
            {{ _('Save') }}
        </button>
        <button v-show="edit" type="button" class="btn btn-primary btn-sm btn-flat pointer pull-left"
            @click="edit = false">
            {{ _('Cancel') }}
        </button>
    </footer>
</modal>
</template>

<script>
import API from 'api';
import CommunityResource from 'models/communityresource';
import Dataset from 'models/dataset';

export default {
    components: {
        'modal': require('components/modal.vue'),
        'community-form': require('components/dataset/resource/form.vue')
    },
    data: function() {
        return {
            edit: false,
            confirm: false,
            community: new CommunityResource(),
        };
    },
    methods: {
        compute_close_url: function() {
            if (this.community.organization) {
                return '/organization/' + this.community.organization.id + '/';
            } else {
                return '/user/' + this.community.owner.id + '/';
            }
        },
        save: function() {
            if (this.$.form.validate()) {
                Object.assign(this.community, this.$.form.serialize());
                if (this.callback) {
                    this.community.on_fetched = this.callback;
                }
                this.community.save();
                this.$go(this.compute_close_url());
                this.$.modal.close();
                return true;
            }
        },
        delete_confirmed: function() {
            API.datasets.delete_community_resource({community: this.community.id},
                (response) => {
                    if (this.callback) {
                        this.callback();
                    }
                    this.$go(this.compute_close_url());
                    this.$.modal.close();
                }
            );
        }
    }
};
</script>
