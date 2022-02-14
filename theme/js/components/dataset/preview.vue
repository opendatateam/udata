<template>
  <vue-final-modal class="modal-wrapper">
    <div class="modal-body">
      <iframe :src="url" width="100%" height="600" frameborder="0"></iframe>
    </div>

    <footer class="modal-footer">
      <button class="fr-btn fr-fi-close-line" @click.prevent="close()" :title="$t('Close')"> {{$t('Close')}} </button>
    </footer>
  </vue-final-modal>
</template>

<script>
export default {
  name: "Preview",
  props: {
    url: String,
    close: Function,
  },
};
</script>
