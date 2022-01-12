<!--
---
name: Suggestor
category: Search
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
* entityUrl: This is the URL that will be called to fetch labels for options provided before the component mounts,
* placeholder: Need I say more ? It's something to hold the place while the thingy is empty or something like that,
* searchPlaceholder: Same as above, but for the input where you can type your request,
* emptyPlaceholder: Placeholder when the search returns null or everything crashed,
* values: Initial values if the select needs to be pre-filled before the user even touches it. Can be a String (single value) or an Array of values.
  Labels will be fetched either from the entityUrl for each value, or from the options list if listUrl is provided, or the value will be used as label.

```
-->
<template>
  <Multiselect
    v-model="value"
    :options="options"
    :delay="delay"
    :maxHeight="450"
    searchable
    :placeholder="placeholder"
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
    <template #multiplelabel="{ values }">
      <div class="multiselect-multiple-label" v-if="!opened">
        <div class="multiselect-tag" v-if="values.length >= 1">
          {{ values[0].label }}
        </div>
        <div class="multiselect-tag more" v-if="values.length > 1">
          + {{ values.length - 1 }}
        </div>
      </div>
      <div v-else />
    </template>
    <template #beforelist v-if="value.length">
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
import Multiselect from "@vueform/multiselect";
import i18n from "../../plugins/i18n";

export default {
  components: {
    Multiselect,
  },
  props: {
    onChange: Function,
    suggestUrl: String,
    listUrl: String,
    entityUrl: String,
    placeholder: String,
    searchPlaceholder: String,
    values: [Array, String],
    emptyPlaceholder: {
      type: String,
      default: i18n.global.t("No results found."),
    },
  },
  mounted() {
    this.$refs.multiselect.$refs.input.ariaLabel =
      this.searchPlaceholder || this.placeholder;
  },
  async created() {
    // If we're in "suggest" mode, the options will be the suggest function that will be called on each search change
    // If not, we call the getInitialOptions fn that will populate the options var
    if (this.suggestUrl) {
      this.options = this.suggest;
      this.delay = 50;
    } else {
      this.options = await this.getInitialOptions();
    }

    // Then we fill the select with existing value if there is any, using the previously made list if needs be
    this.fillInitialValues();
  },
  data() {
    return {
      value: [], // Current selected value(s) object array `[{label: 'A', value: 'a'}, {label: 'B', value: 'b'}]`
      opened: false, // Tracks whether the select is open
      options: null, // Current options list, same structure as `value` above (but contains all possible options). Can be dynamic (async)
      delay: -1, // Disable async loading
    };
  },
  watch: {
    opened(value) {
      if(value) {
        this.$refs.multiselect.$refs.input.placeholder = this.searchPlaceholder || this.placeholder;
      } else {
        this.$refs.multiselect.$refs.input.placeholder = '';
      }
    },
    values (value) {
      // This lib doesn't support `undefined` values and will not reset its state.
      // This allows to reset the value if the parent component decides to clear the value.
      if (typeof value === "undefined") this.value = [];
    },
  },
  methods: {
    suggest: function (q) {
      let query;

      // For collections with no listing URL, if no `q` is given we can return early because the suggest API will return no results.
      if (!q && !this.listUrl) return Promise.resolve([]);

      // On initial render, q will be undefined. We fetch the collection instead of fetching a suggest result using the listUrl
      if (!q) {
        query = this.$api.get(this.listUrl).then((resp) => resp.data.data);
      } else {
        query = this.$api
          .get(this.suggestUrl, { params: { q } })
          .then((resp) => resp.data);
      }
      return query.then(this.serializer);
    },
    fillInitialValues: function () {
      // On creation, if values are pre-provided by the parent (from URL or parent state) in `this.values`,
      // we have to fetch those from the API to fill the select with values + labels in `this.value`
      // `this.values` can be a single value (String) or an array of values so we need to normalize it

      let selected = null;
      if (typeof this.values === "string") {
        selected = [this.values];
      } else if (Array.isArray(this.values)) {
        selected = this.values;
      } else {
        selected = [];
      }

      // Now for each value, three cases :
      // * We have a entityUrl prop that we will call for each value to get the corresponding label
      // * We don't have a entityUrl but we have an option list that we can search into
      // * We have nothing, YOLO let's simply use the value as a label
      selected.forEach(async (value) => {
        let label = value;

        if (this.entityUrl) {
          // Fetch it from API
          let entity = await this.$api
            .get(this.entityUrl + value)
            .then((resp) => resp.data)
            .then((data) => this.serializer([data]));

          if (entity.length >= 1) label = entity[0].label;
        } else if (this.options?.length > 0) {
          // Find it in the options list
          let option = Object.keys(this.options).find(
            (opt) => this.options[opt].value === value
          );

          // If found, populate
          option = this?.options[option];
          if (option) label = option.label;
        }

        this.value.push({ label, value });
      });
    },
    getInitialOptions: async function () {
      if (!this.listUrl) return [];

      return await this.$api
        .get(this.listUrl)
        .then((resp) => resp.data)
        .then(this.serializer);
    },
    // Tries to guess values and labels. Harder than it looks.
    serializer (data) {
      return data.map((obj) => ({
        label: obj.name || obj.title || obj.text || obj?.properties?.name,
        value: obj.id || obj.text,
      }));
    },
    onSelect () {
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
