<template>
<modal class="resource-modal" v-ref:modal
    :title="resource.title">

    <div class="modal-body">
        {{{ resource.description|markdown }}}

        <dl class="dl-horizontal dl-wide">
          <dt>{{ _('URL') }}</dt>
          <dd><a :href="resourceJsonLd.contentUrl" @click="onClick">{{resourceJsonLd.contentUrl}}</a></dd>
          <dt>{{ _('Latest URL') }}</dt>
          <dd><a :href="resourceJsonLd.url" @click="onClick">{{resourceJsonLd.url}}</a></dd>
          <dt v-if="resourceJsonLd.encodingFormat">{{ _('Format') }}</dt>
          <dd v-if="resourceJsonLd.encodingFormat">{{resourceJsonLd.encodingFormat}}</dd>
          <dt v-if="resourceJsonLd.fileFormat">{{ _('MimeType') }}</dt>
          <dd v-if="resourceJsonLd.fileFormat">{{resourceJsonLd.fileFormat}}</dd>
          <dt v-if="resourceJsonLd.contentSize">{{ _('Size') }}</dt>
          <dd v-if="resourceJsonLd.contentSize">{{ resourceJsonLd.contentSize|size }}</dd>
          <dt v-if="resourceJsonLd.checksum">{{ resourceJsonLd.checksumType || 'sha1'}}</dt>
          <dd v-if="resourceJsonLd.checksum">{{ resourceJsonLd.checksum }}</dd>
          <dt v-if="resourceJsonLd.dateCreated">{{ _('Created on') }}</dt>
          <dd v-if="resourceJsonLd.dateCreated"> {{ resourceJsonLd.dateCreated|dt }}</dd>
          <dt v-if="resourceJsonLd.dateModified">{{ _('Modified on') }}</dt>
          <dd v-if="resourceJsonLd.dateModified"> {{ resourceJsonLd.dateModified|dt }}</dd>
          <dt v-if="resourceJsonLd.datePublished">{{ _('Published on') }}</dt>
          <dd v-if="resourceJsonLd.datePublished"> {{ resourceJsonLd.datePublished|dt }}</dd>
          <dt v-if="resourceJsonLd.interactionStatistic && resourceJsonLd.interactionStatistic.userInteractionCount">{{ _('Downloads') }}</dt>
          <dd v-if="resourceJsonLd.interactionStatistic && resourceJsonLd.interactionStatistic.userInteractionCount"> {{ resourceJsonLd.interactionStatistic.userInteractionCount }}</dd>
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
import Modal from 'components/modal.vue';
import Resource from 'models/resource';
import Availability from './resource/availability.vue';
import pubsub from 'pubsub';

export default {
    props: {
        datasetId: {
            type: String,
            required: true,
        },
        resourceId: {
            type: String,
            required: true,
        },
        resourceJsonLd: {
            type: Object,
            required: true,
        }
    },
    data() {
        return {
            resource: new Resource(),
        }
    },
    components: {Modal, Availability},
    created() {
        this.resource.fetch(this.datasetId, this.resourceId);
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
        }
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
