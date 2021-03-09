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
    emptyPlaceholder: {
      type: String,
      default: "Aucun résultat.",
    },
  },
  mounted() {
    //Little library hacking to add a placeholder to the search input
    this.$refs.multiselect.$refs.input.placeholder =
      this.searchPlaceholder || this.placeholder;
  },
  async created() {
    //If we're in "suggest" mode, the options will be the suggest function that will be called on each search change
    //If not, we call the getInitialOptions fn that will populate the options var
    if (this.suggestUrl) this.options = this.suggest;
    else this.options = await this.getInitialOptions();
  },
  data() {
    return {
      value: [],
      loading: false,
      opened: false,
      options: null,
    };
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

      //todo : better serializer
      return query.then((data) =>
        data.map((obj) => ({
          label: obj.name,
          value: obj.id,
        }))
      );
    },
    getInitialOptions: async function () {
      if (!this.listUrl) return [];

      return await this.$api
        .get(this.listUrl)
        .then((resp) => resp.data)
        .then((data) =>
          data.map((obj) => ({ label: obj.name || obj.title, value: obj.id }))
        );
    },
    deselect: function (value) {
      if (this.$refs.multiselect) this.$refs.multiselect.deselect(value);
    },
  },
};
</script>
