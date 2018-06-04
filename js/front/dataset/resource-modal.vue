<template>
<modal class="resource-modal" v-ref:modal :title="resource.title">

    <div class="modal-body">
        {{{ resource.description|markdown }}}

        <dl class="dl-horizontal dl-wide">
          <dt>{{ _('URL') }}</dt>
          <dd><a :href="resource.url" @click="onClick">{{resource.url}}</a></dd>
          <dt>{{ _('Latest URL') }}</dt>
          <dd><a :href="resource.latest" @click="onClick">{{resource.latest}}</a></dd>
          <dt v-if="resourceType">{{ _('Type') }}</dt>
          <dd v-if="resourceType">{{ resourceType }}</dd>
          <dt v-if="resource.format">{{ _('Format') }}</dt>
          <dd v-if="resource.format">{{resource.format}}</dd>
          <dt v-if="resource.mime">{{ _('MimeType') }}</dt>
          <dd v-if="resource.mime">{{resource.mime}}</dd>
          <dt v-if="resource.filesize">{{ _('Size') }}</dt>
          <dd v-if="resource.filesize">{{ resource.filesize|size }}</dd>
          <dt v-if="resource.checksum">{{ resource.checksumType || 'sha1'}}</dt>
          <dd v-if="resource.checksum">{{ resource.checksum }}</dd>
          <dt v-if="resource.created_at">{{ _('Created on') }}</dt>
          <dd v-if="resource.created_at"> {{ resource.created_at|dt }}</dd>
          <dt v-if="resource.modified">{{ _('Modified on') }}</dt>
          <dd v-if="resource.modified"> {{ resource.modified|dt }}</dd>
          <dt v-if="resource.published">{{ _('Published on') }}</dt>
          <dd v-if="resource.published"> {{ resource.published|dt }}</dd>
          <dt v-if="resource.metrics && resource.metrics.views">{{ _('Downloads') }}</dt>
          <dd v-if="resource.metrics && resource.metrics.views"> {{ resource.metrics.views }}</dd>
          <dt v-if="resource.extras && resource.extras['check:date']">{{ _('Last checked on') }}</dt>
          <dd v-if="resource.extras && resource.extras['check:date']"> {{ resource.extras['check:date']|dt }}</dd>
          <dt v-if="resource.extras && resource.extras['check:status']">{{ _('Last checked result') }}</dt>
          <dd v-if="resource.extras && resource.extras['check:status']">
                <availability :status="resource.extras['check:status']"></availability>
          </dd>
        </dl>
    </div>

    <footer class="modal-footer text-center">
        <a :href="resource.url" class="btn btn-success" @click="onClick">
            {{ _('Download') }}
        </a>
    </footer>
</modal>
</template>

<script>
import Availability from './resource/availability.vue';
import Modal from 'components/modal.vue';
import pubsub from 'pubsub';
import Resource from 'models/resource';
import resource_types from 'models/resource_types';

export default {
    props: {
        datasetId: {
            type: String,
            required: true,
        },
        resource: {
            type: Object,
            required: true,
        }
    },
    components: {Modal, Availability},
    data() {
        return {
            resourceType: undefined,
        }
    },
    created() {
        const url = `datasets/${this.datasetId}/resources/${this.resource.id}/`;
        this.$api.get(url).then(resource => {
            Object.assign(this.resource, resource);
        });
        // ensure this will be filled both on open from dataset page and direct open (deeplink)
        if (resource_types.has_data) {
            this.fillResourceType();
        } else {
            resource_types.$on('updated', (res) => {
                this.fillResourceType();
            });
        }
    },
    methods: {
        onClick() {
            let eventName;
            if (this.resource.url.startsWith(window.location.origin)) {
                eventName = 'RESOURCE_DOWNLOAD';
            } else {
                eventName = 'RESOURCE_REDIRECT';
            }
            pubsub.publish(eventName);
            this.$refs.modal.close();
        },
        fillResourceType() {
            if (this.resource.type) {
                this.resourceType = resource_types.by_id(this.resource.type).label;
            }
        },
    }
};
</script>

<style lang="less">
.resource-modal {
    .dl-wide dd {
        // URLs and hashes are not breakable on words
        word-break: break-all;
    }
}
</style>
