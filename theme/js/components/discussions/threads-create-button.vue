<template>
  <button
    class="fr-btn fr-btn--secondary btn-secondary btn-secondary-grey-500 fr-fi-add-line fr-btn--icon-left"
    @click.prevent="click"
  >
    {{ $t('Start a new discussion') }}
  </button>
</template>

<script>
export default {
  props: {
    onClick: {
      type: Function,
    }
  },
  methods: {
    click() {
      return this.onClick? this.onClick() : this.$bus.emit('discussions.startThread');
    }
  }
}
</script>
