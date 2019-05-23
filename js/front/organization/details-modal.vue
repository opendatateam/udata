<template>
<modal class="extras-modal" v-ref:modal :title="_('Details')">

    <div class="modal-body">
        <dl class="dl-horizontal dl-wide">
          <dt>{{ _('ID') }}</dt>
          <dd><a href="/organizations/{{organization['@id']}}">{{organization['@id']}}</a></dd>
          <dt v-if="organization.dateCreated">{{ _('Created on') }}</dt>
          <dd v-if="organization.dateCreated"> {{ organization.dateCreated|dt }}</dd>
          <dt v-if="organization.dateModified">{{ _('Modified on') }}</dt>
          <dd v-if="organization.dateModified"> {{ organization.dateModified|dt }}</dd>
        </dl>

    </div>

    <footer class="modal-footer text-center">
        <button class="btn btn-default" @click="$refs.modal.close">
            {{ _('Close') }}
        </button>
    </footer>
</modal>
</template>

<script>
import Modal from 'components/modal.vue';

export default {
    props: {
        organization: Object
    },
    components: {Modal}
};
</script>
