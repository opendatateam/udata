<!--
---
name: Suggestor
category: Interactions
---

# Suggestor

A pretty complex component that looks like a `<select>` but with many hidden features :

* Initial values can be provided from props (can be used to pre-fill the select with values from the URL)
* Options can be either a list from an API that will be fetched on component load and then never change
* Or it can be a dynamic suggest-style API that will be fetched on each character the user types in the select
* Or it can be a combination of both : a static list on component load that is then replaced by a suggest system when the user types something

## Usage

Simply provide the many necessary props :

* onChange: Function that will be called on each value select/deselect action,
* suggestUrl: This is the URL that will be called (if provided) when the user performs a search within the select.
 If not provided, suggest mode will be disabled and typing in the select will only filter the existing options.
* listUrl: This is the URL that will be called to populate the select options on mount.
If not provided, the select will start empty and will fill with options when the user starts typing some text,
* placeholder: Need I say more ? It's something to hold the place while the thingy is empty or something like that,
* searchPlaceholder: Same as above, but for the input where you can type your request,
* emptyPlaceholder: Placeholder when the search returns null or everything crashed,
* values: Initial values if the select needs to be pre-filled before the user even touches it. Can be a String (single value) or an Array of values.
  Passing a label is not supported currently, but should be one day (quite trivial). Maybe one day labels should be fetched from an external API.
  For now, we simply use the provided value(s) as label(s)

```
-->
<template>
  <Multiselect
    v-model="value"
    :options="options"
    :delay="50"
    :maxHeight="450"
    searchable
    :placeholder="opened ? '' : placeholder"
    :noOptionsText="emptyPlaceholder"
    :noResultsText="emptyPlaceholder"
    mode="multiple"
    class="suggestor"
    @change="onChange"
    @select="onSelect"
    @open="opened = true"
    @close="opened = false"
    object
    ref="multiselect"
  >
    <template v-slot:multiplelabel="{ values }">
      <div class="suggestor-labels" v-if="!opened">
        <div class="multiselect-tag" v-if="values.length >= 1">
          {{ values[0].label }}
        </div>
        <div class="multiselect-tag more" v-if="values.length > 1">
          + {{ values.length - 1 }}
        </div>
      </div>
      <div v-else />
    </template>
    <template v-slot:beforelist v-if="value.length">
      <div class="suggestor-search-labels is-opened">
        <div class="multiselect-tag" v-for="v in value">
          <span>{{ v.label }}</span>
          <i @mousedown.prevent.stop="deselect(v)"></i>
        </div>
      </div>
    </template>
  </Multiselect>
</template>

<script>
import config from "../../config";
import Multiselect from "@vueform/multiselect";
import "@vueform/multiselect/themes/default.css";

export default {
  components: {
    Multiselect,
  },
  props: {
    onChange: Function,
    suggestUrl: String,
    listUrl: String,
    placeholder: String,
    searchPlaceholder: String,
    values: [Array, String],
    emptyPlaceholder: {
      type: String,
      default: "Aucun résultat.",
    },
  },
  mounted() {
    //Little library hacking to add a placeholder to the search input when the selector is open
    this.$refs.multiselect.$refs.input.placeholder =
      this.searchPlaceholder || this.placeholder;
  },
  async created() {
    //We start by filling the select with existing value if there is any
    this.fillInitialValues();

    //If we're in "suggest" mode, the options will be the suggest function that will be called on each search change
    //If not, we call the getInitialOptions fn that will populate the options var
    if (this.suggestUrl) this.options = this.suggest;
    else this.options = await this.getInitialOptions();
  },
  data() {
    return {
      value: [], //Current selected value(s) object array `[{label: 'A', value: 'a'}, {label: 'B', value: 'b'}]`
      opened: false, //Tracks whether the select is open
      options: null, //Current options list, same structure as `value` above (but contains all possible options). Can be dynamic (async)
    };
  },
  watch: {
    values: function (value) {
      //This lib doesn't support `undefined` values and will not reset its state.
      //This allows to reset the value if the parent component decides to clear the value.
      if (typeof value === "undefined") this.value = [];
    },
  },
  methods: {
    suggest: function (q) {
      let query;

      //For collections with no listing URL, if no `q` is given we can return early because the suggest API will return no results.
      if (!q && !this.listUrl) return Promise.resolve([]);

      //On initial render, q will be undefined. We fetch the collection instead of fetching a suggest result using the listUrl
      if (!q)
        query = this.$api.get(this.listUrl).then((resp) => resp.data.data);
      else
        query = this.$api
          .get(this.suggestUrl, { params: { q } })
          .then((resp) => resp.data);

      return query.then(this.serializer);
    },
    fillInitialValues: function () {
      //On creation, if values are pre-provided by the parent (from URL or parent state) in `this.values`,
      //we should be fetching those from the API to fill the select with values + labels in `this.value`
      //This isn't ideal but shouldn't happen very often.
      //In the meantime, since this is a bit too complicated we'll just fill the select with the "value" as label.

      //`this.values` can be a single value (String) or an array of values so we need to normalize it
      let selected = null;
      if (typeof this.values === "string") selected = [this.values];
      else if (typeof this.values === "array") selected = this.values;
      else selected = [];

      selected.forEach((value) => this.value.push({ label: value, value }));
    },
    getInitialOptions: async function () {
      if (!this.listUrl) return [];

      return await this.$api
        .get(this.listUrl)
        .then((resp) => resp.data)
        .then(this.serializer);
    },
    serializer: function (data) {
      return data.map((obj) => ({
        label: obj.name || obj.title || obj.text,
        value: obj.id || obj.text,
      }));
    },
    onSelect: function (value) {
      //This is a temporary dirty thing that limits the selected options to 1.
      if (this.value.length === 2) {
        this.deselect(this.value[0]);
        this.$refs.multiselect.close();
      }
    },
    deselect: function (value) {
      if (this.$refs.multiselect) this.$refs.multiselect.deselect(value);
    },
  },
};
</script>
