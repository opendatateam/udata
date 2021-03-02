<template>
  <Multiselect
    v-model="value"
    :options="suggest"
    :delay="50"
    :maxHeight="450"
    searchable
    :placeholder="placeholder"
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
    <template v-slot:beforelist>
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
  mounted() {
    if (!this.listUrl) this.listUrl = this.suggestUrl;
    if (!this.suggestUrl) this.suggestUrl = this.listUrl;
  },
  props: {
    onChange: Function,
    suggestUrl: String,
    listUrl: String,
    placeholder: String,
  },
  data() {
    return {
      value: [],
      loading: false,
      opened: false,
    };
  },
  methods: {
    suggest: function (q) {
      let query;

      //On initial render, q will be undefined. We fetch the collection instead of fetching a suggest result using the listUrl
      if (!q)
        query = this.$api.get(this.listUrl).then((resp) => resp.data.data);
      else
        query = this.$api
          .get(this.suggestUrl, { params: { q } })
          .then((resp) => resp.data);

      return query.then((data) =>
        data.map((obj) => ({
          label: obj.name,
          value: obj.id,
        }))
      );
    },
    deselect: function (value) {
      if (this.$refs.multiselect) this.$refs.multiselect.deselect(value);
    },
  },
};
</script>
