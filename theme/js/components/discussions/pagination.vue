<template>
  <ul class="pagination-wrapper">
    <li>
      <a
        :class="['first', page === 1 ? 'disabled' : '']"
        @click.prevent="_onClick(1)"
        >«</a
      >
    </li>
    <li>
      <a
        :class="['previous', page === 1 ? 'disabled' : '']"
        @click.prevent="_onClick(page - 1)"
        ><</a
      >
    </li>
    <li v-for="index in pages">
      <a
        :class="[page === index ? 'active' : '']"
        @click.prevent="_onClick(index)"
        >{{ index }}</a
      >
    </li>
    <li>
      <a
        :class="['next', page === pages.length ? 'disabled' : '']"
        @click.prevent="_onClick(page + 1)"
        >></a
      >
    </li>
    <li>
      <a
        :class="['last', page === pages.length ? 'disabled' : '']"
        @click.prevent="_onClick(pages.length)"
        >»</a
      >
    </li>
  </ul>
</template>

<script>
export default {
  props: {
    page: Number,
    changePage: Function,
    page_size: Number,
    total_results: Number,
  },
  computed: {
    pages() {
      return [
        ...Array(Math.ceil(this.total_results / this.page_size)).keys(),
      ].map((k) => k + 1);
    },
  },
  methods: {
    _onClick(index) {
      if (index !== this.page) return this.changePage(index);
    },
  },
};
</script>
