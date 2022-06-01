<template>
  <vue-final-modal class="modal-wrapper">
    <div class="modal-body">
      <iframe :src="url" width="100%" height="600" frameborder="0" :title="$t('Preview of resource X', {title})"></iframe>
    </div>

    <footer class="modal-footer">
      <button class="fr-btn fr-icon-close-line" @click.prevent="close()" :title="$t('Close')"> {{$t('Close')}} </button>
    </footer>
  </vue-final-modal>
</template>

<script>
export default {
  name: "Preview",
  props: {
    url: String,
    close: Function,
    title: String,
  },
};
</script>
