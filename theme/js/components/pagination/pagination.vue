<!--
---
name: Pagination
category: Interactions
---

# Pagination

A simple pagination Vue component that allow you to paginate long collections.

## Usage

Simply provide necessary props :

* page : current page
* page_size : page... size. How many elements will be on each page
* total_results : total collection length
* changePage : a function that will be called on each button click. It will be passed a single argument : the new page number

Check the example below for more infos :

```pagination-ex.vue
<template>
    <pagination
      v-if="total_results > page_size"
      :page="current_page"
      :page_size="page_size"
      :total_results="total_results"
      :changePage="changePage"
    />
</template>

<script>
import Pagination from "../components/pagination/pagination.vue"

export default {
  name: "XXX",
  components: {
      Pagination
  },
  methods: {
    changePage(index) {
      this.page = index; //Change current page
      this.loadPage(); //Load corresponding new info
      scrollToTop(); //Then scroll to the top
    }
  }
};
</script>
```
-->

<template>
  <ul class="pagination-wrapper" role="navigation" aria-label="pagination">
    <li>
      <a
        :class="['first', page === 1 ? 'disabled' : '']"
        :aria-disabled="page === 1"
        @click.prevent="_onClick(1)"
        >«</a
      >
    </li>
    <li>
      <a
        :class="['previous', page === 1 ? 'disabled' : '']"
        :aria-disabled="page === 1"
        @click.prevent="_onClick(page - 1)"
        >&lt;</a
      >
    </li>
    <li v-for="index in pages">
      <a
        :class="[page === index ? 'active' : false]"
        :aria-current="page === index ? 'page' : false"
        @click.prevent="_onClick(index)"
        >{{ index }}</a
      >
    </li>
    <li>
      <a
        :class="['next', page === pages.length ? 'disabled' : '']"
        :aria-disabled="page === pages.length"
        @click.prevent="_onClick(page + 1)"
        >&gt;</a
      >
    </li>
    <li>
      <a
        :class="['last', page === pages.length ? 'disabled' : '']"
        :aria-disabled="page === pages.length"
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
