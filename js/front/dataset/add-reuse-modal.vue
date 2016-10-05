<template>
<modal class="add-reuse-modal" v-ref:modal :title="_('Add a reuse')">
    <div class="modal-body">
        <p>{{ _('You can either add a new reuse or an existing one') }}</p>
        <div class="row reuses-list in-modal">
            <div class="col-sm-6 col-md-4">
                <a class="thumbnail reuse add" :href="formUrl">
                    <div class="preview">+</div>
                    <div class="caption">
                        <h4>{{ _('New reuse') }}</h4>
                    </div>
                </a>
            </div>
            <div v-for="reuse in reuses" class="col-sm-6 col-md-4">
                <a class="thumbnail reuse clickable" :title="reuse.title"
                    @click.prevent="addToReuse(reuse.id)">
                    <div class="preview">
                        <img class="media-object img-responsive" :alt="reuse.title" :src="reuse.image">
                    </div>
                    <div class="caption">
                        <h4>{{ reuse.title }}</h4>
                    </div>
                </a>
            </div>
        </div>
    </div>
</modal>
</template>

<script>
import config from 'config';
import Modal from 'components/modal.vue';

export default {
    props: {
        dataset: Object,
        reuses: Array,
        formUrl: String
    },
    components: {Modal},
    methods: {
        addToReuse(id) {
            const url = `reuses/${id}/datasets/`;
            const data = {id: this.dataset['@id'], class: 'Dataset'};
            this.$api.post(url, data).then(() => {
                window.location = `${config.admin_root}reuse/${id}`;
            });
        }
    }
};
</script>
