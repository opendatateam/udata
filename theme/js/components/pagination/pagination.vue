<!--
---
name: Pagination
category: 5 - Interactions
---

# Pagination

A simple pagination Vue component that allow you to paginate long collections.

## Usage

Simply provide necessary props :

* page : current page
* page_size : how many elements will be on each page
* total_results : total collection length
* changePage : a function that will be called on each button click. It will be passed a single argument : the new page number

Check the example below for more infos :

```pagination-ex.vue
<template>
    <pagination
      v-if="totalResults > pageSize"
      :page="currentPage"
      :page-size="pageSize"
      :total-results="totalResults"
      :change-page="changePage"
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
      this.page = index; // Change current page
      this.loadPage(); // Load corresponding new info
      scrollToTop(); // Then scroll to the top
    }
  }
};
</script>
```
-->

<template>
  <nav role="navigation" class="fr-pagination fr-pagination--centered" aria-label="Pagination">
    <ul class="fr-pagination__list">
      <li>
        <a
          :href="page === 1 ? null :'#'"
          class="fr-pagination__link fr-pagination__link--first"
          @click.prevent="_onClick(1)"
        >
          {{ $t('First page') }}
        </a>
      </li>
      <li>
        <a
          :href="page === 1 ? null : '#'"
          class="fr-pagination__link fr-pagination__link--prev fr-pagination__link--lg-label"
          @click.prevent="previousPage"
        >
          {{ $t('Previous page') }}
        </a>
      </li>
      <li>
        <a
          :aria-current="page === 1 ? 'page' : null"
          :href="page === 1 ? null : '#'"
          class="fr-pagination__link"
          :class="{'fr-hidden fr-unhidden-sm': page > 1}"
          :title="$t('Page', {nb: 1})"
          @click.prevent="_onClick(1)"
        >
          1
        </a>
      </li>
      <li v-for="index in visiblePages">
        <a
          class="fr-pagination__link"
          :class="{'fr-hidden fr-unhidden-lg': index < page - 1 || index > page + 1}"
          :aria-current="page === index ? 'page' : null"
          :href="page === index ? null : '#'"
          :title="$t('Page', {nb: index})"
          @click.prevent="_onClick(index)"
          v-if="index"
          >
          {{ index }}
        </a>
        <a class="fr-pagination__link fr-hidden fr-unhidden-lg" v-else>
          …
        </a>
      </li>
      <li>
        <a
          class="fr-pagination__link"
          :aria-current="page === pageCount ? 'page' : null"
          :href="page === pageCount ? null : '#'"
          :title="$t('Page', {nb: pageCount})"
          @click.prevent="_onClick(pageCount)"
        >
          {{ pageCount }}
        </a>
      </li>
      <li>
        <a
          class="fr-pagination__link fr-pagination__link--next fr-pagination__link--lg-label"
          :href="page === pageCount ? null : '#'"
          @click.prevent="nextPage"
        >
          {{ $t('Next page') }}
        </a>
      </li>
      <li>
        <a
          class="fr-pagination__link fr-pagination__link--last"
          :href="page === pageCount ? null : '#'"
          @click.prevent="_onClick(pageCount)"
        >
          {{ $t('Last page') }}
        </a>
      </li>
    </ul>
  </nav>
</template>

<script>
import getVisiblePages from "../vanilla/pagination";

export default {
  props: {
    page: Number,
    changePage: Function,
    pageSize: Number,
    totalResults: Number,
  },
  data() {
    return {
      pagesAround: 3
    }
  },
  computed: {
    pageCount() {
      return Math.ceil(this.totalResults / this.pageSize);
    },
    visiblePages() {
      return getVisiblePages(this.page, this.pageCount);
    },
  },
  methods: {
    _onClick(index) {
      if (index !== this.page) {
        return this.changePage(index);
      }
    },
    nextPage() {
      const index = this.page + 1;
      if (index <= this.pageCount) {
        return this.changePage(index);
      }
    },
    previousPage() {
      const index = this.page - 1;
      if (index > 0) {
        return this.changePage(index);
      }
    }
  },
};
</script>
