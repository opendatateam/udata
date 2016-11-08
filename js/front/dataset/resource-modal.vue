<template>
<modal class="resource-modal" v-ref:modal
    :title="resource.name">

    <div class="modal-body">
        {{{ resource.description }}}

        <dl class="dl-horizontal dl-wide">
          <dt>{{ _('URL') }}</dt>
          <dd><a :href="resource.contentUrl" @click="onClick">{{resource.contentUrl}}</a></dd>
          <dt>{{ _('Latest URL') }}</dt>
          <dd><a :href="resource.url" @click="onClick">{{resource.url}}</a></dd>
          <dt v-if="resource.encodingFormat">{{ _('Format') }}</dt>
          <dd v-if="resource.encodingFormat">{{resource.encodingFormat}}</dd>
          <dt v-if="resource.fileFormat">{{ _('MimeType') }}</dt>
          <dd v-if="resource.fileFormat">{{resource.fileFormat}}</dd>
          <dt v-if="resource.contentSize">{{ _('Size') }}</dt>
          <dd v-if="resource.contentSize">{{ resource.contentSize|size }}</dd>
          <dt v-if="resource.checksum">{{ resource.checksumType || 'sha1'}}</dt>
          <dd v-if="resource.checksum">{{ resource.checksum }}</dd>
          <dt v-if="resource.dateCreated">{{ _('Created on') }}</dt>
          <dd v-if="resource.dateCreated"> {{ resource.dateCreated|dt }}</dd>
          <dt v-if="resource.dateModified">{{ _('Modified on') }}</dt>
          <dd v-if="resource.dateModified"> {{ resource.dateModified|dt }}</dd>
          <dt v-if="resource.datePublished">{{ _('Published on') }}</dt>
          <dd v-if="resource.datePublished"> {{ resource.datePublished|dt }}</dd>
          <dt v-if="resource.interactionStatistic && resource.interactionStatistic.userInteractionCount">{{ _('Downloads') }}</dt>
          <dd v-if="resource.interactionStatistic && resource.interactionStatistic.userInteractionCount"> {{ resource.interactionStatistic.userInteractionCount }}</dd>
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
import pubsub from 'pubsub';

export default {
    props: {
        resource: Object
    },
    components: {Modal},
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
