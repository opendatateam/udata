<template>
  <button
    class="fr-btn fr-btn--secondary fr-btn--secondary-grey-500 fr-icon-add-line fr-btn--icon-left"
    @click.prevent="click"
  >
    {{ $t('Start a new discussion') }}
  </button>
</template>

<script>
import {defineComponent} from "vue";
import {DISCUSSIONS_START_THREAD} from "../../plugins/eventbus";

export default defineComponent({
  props: {
    onClick: {
      type: Function,
    }
  },
  methods: {
    click() {
      return this.onClick? this.onClick() : this.$bus.emit(DISCUSSIONS_START_THREAD);
    }
  }
});
</script>
