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
* light : optional param that will add a `.light` class and trigger the corresponding color scheme

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
  <ul
    class="pagination-wrapper"
    :class="{ light }"
    role="navigation"
    aria-label="pagination"
  >
    <li>
      <a
        :class="{ disabled: page === 1 }"
        class="previous"
        :aria-disabled="page === 1"
        @click.prevent="_onClick(page - 1)"
      ></a>
    </li>
    <li>
      <a
        :class="{ active: page === 1 }"
        :aria-disabled="page === 1"
        @click.prevent="_onClick(1)"
        >1</a
      >
    </li>
    <li v-for="index in visible_pages">
      <a
        :class="{ active: page === index }"
        :aria-current="page === index ? 'page' : false"
        @click.prevent="_onClick(index)"
        v-if="index"
        >{{ index }}</a
      >
      <span class="ellipsis" role="img" aria-label="ellipsis" aria-hidden="true" v-else>...</span>
    </li>
    <li>
      <a
        :class="{ active: page === pages.length }"
        :aria-disabled="page === pages.length"
        @click.prevent="_onClick(pages.length)"
        >{{ pages.length }}</a
      >
    </li>
    <li>
      <a
        :class="{ disabled: page === pages.length }"
        class="next"
        :aria-disabled="page === pages.length"
        @click.prevent="_onClick(page + 1)"
      ></a>
    </li>
  </ul>
</template>

<script>
function range(size, startAt = 1) {
  return [...Array(size).keys()].map((i) => i + startAt);
}

export default {
  props: {
    page: Number,
    changePage: Function,
    page_size: Number,
    total_results: Number,
    light: Boolean,
  },
  computed: {
    pages() {
      return range(Math.ceil(this.total_results / this.page_size));
    },
    visible_pages() {
      const length = this.pages.length;
      const pagesAround = 1; //Pages around current one
      const pagesShown = Math.min(pagesAround * 2 + 1, length);

      if (length < pagesAround + 2) return [];

      if (this.page <= pagesShown) return [...range(pagesShown, 2), null];

      if (this.page >= length - pagesShown + 1)
        return [null, ...range(pagesShown, length - pagesShown)];

      return [null, ...range(pagesShown, this.page - pagesAround), null];
    },
  },
  methods: {
    _onClick(index) {
      if (index !== this.page) return this.changePage(index);
    },
  },
};
</script>
