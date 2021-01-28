<!--
---
name: Search
category: Interactions
---

# Search input

It's an input that searches with an autocomplete (typeahead) feature.
It searches using uData search API using separate API calls for Datasets and Reuses

## Architecture

The search is composed with multiple components :

* `<search-input>` is an input in which you can type and get instant results in a dropdown, with links to see more results`
* `<search-trigger>` is going to be an element that can look like anything you'd like (including an input) and will actually trigger the "real" search when interacted with. It'll be used in the header and the home page.
* `<search-suggestions>` is going to be the component that displays the search suggestions after you search for something.
* `<search-facets>` is going to be the one-pager form for refining your search with multiple dimensions

## Progressive enhancement

We're doing progressive enhancement on this component.
This mean that users without Javascript will see a standard search input box that will redirect themto the `/search?q=query` endpoint.

In order to achieve this, the Jinja HTML template includes our Vue `<search-box>` element, which wraps a perfectly functionnal HTML form + input.
However, this also means that our VueJS template will replace everything contained inside this tag.
This is why we also have the same HTML form + input structure in the
VueJS template.

-->

<template>
  <section class="search-input">
    <form action="" @submit.prevent="onSubmit">
      <input
        type="text"
        v-model="queryString"
        @keyup="_onChange"
        :placeholder="$t('Search...')"
      />
    </form>
  </section>
</template>

<script>
export default {
  props: {
    onChange: Function,
  },
  data() {
    return {
      queryString: ""
    };
  },
  methods: {
    _onChange() {
      if(this.onChange)
        this.onChange(this.queryString)
    },
    onSubmit(ev) {
      //TODO : On submit, redirect to search results ?
    },
  },
};
</script>
