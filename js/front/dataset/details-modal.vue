<template>
<modal class="extras-modal" v-ref:modal :title="_('Details')">

    <div class="modal-body">
        <dl class="dl-horizontal dl-wide">
          <dt>{{ _('ID') }}</dt>
          <dd><a href="/datasets/{{dataset['@id']}}">{{dataset['@id']}}</a></dd>
          <dt v-if="dataset.dateCreated">{{ _('Created on') }}</dt>
          <dd v-if="dataset.dateCreated"> {{ dataset.dateCreated|dt }}</dd>
          <dt v-if="dataset.dateModified">{{ _('Modified on') }}</dt>
          <dd v-if="dataset.dateModified"> {{ dataset.dateModified|dt }}</dd>
          <dt v-if="dataset.datePublished">{{ _('Published on') }}</dt>
          <dd v-if="dataset.datePublished"> {{ dataset.datePublished|dt }}</dd>
        </dl>

        <div v-if="dataset.keywords && dataset.keywords.length">
            <h4>{{ _('Tags') }}</h4>
            <div class="label-list tags">
                <a v-for="keyword in dataset.keywords"
                    href="/search?tag={{keyword}}"
                    class="label label-default"
                    :title="keyword">
                    {{ keyword }}
                </a>
            </div>
        </div>

        <div v-if="dataset.extras.length">
            <h4>{{ _('Extra attributes') }}</h4>
            <table class="table table-hover table-striped table-bordered">
                <thead>
                    <tr>
                        <th>{{ _('Key') }}</th>
                        <th>{{ _('Value') }}</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="extra in dataset.extras">
                        <td>{{ extra.name }}</td>
                        <td>{{ extra.value }}</td>
                    </tr>
                </tbody>
            </table>
        </div>
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
        dataset: Object
    },
    components: {Modal}
};
</script>
