<!--
---
name: Rangepicker
category: Search
---

# Rangepicker

Used to pick dates (the calendar kind, unfortunately) for temporal coverage selection.
Supports getting passed a value in the `value` prop (useful to pass value from URL), will call onChange fn on change.

Value format is composed of the two dates forming a range (starting date d1 and ending date d2) as such :

d1.yyyy-d1.mm-d1.dd-d2.yyyy-d2.mm-d2.dd

-->

<template>
  <div class="rangepicker row-inline w-100 justify-between">
    <div class="row-inline align-items-center">
      <strong class="text-grey-300 f-normal mr-xxs">{{ $t("@@du") }}</strong>
      <Datepicker
        v-model="dateRange.start"
        :upperLimit="dateRange.end"
        @update:modelValue="_onChange"
        placeholder="__/__/__"
        :locale="locale"
      />
    </div>
    <div class="row-inline align-items-center">
      <strong class="text-grey-300 f-normal mr-xxs ml-xs">{{
        $t("@@au")
      }}</strong>
      <Datepicker
        v-model="dateRange.end"
        :lowerLimit="dateRange.start"
        @update:modelValue="_onChange"
        placeholder="__/__/__"
        :locale="locale"
      />
    </div>
  </div>
</template>

<script>
import config from "../../config";
import Datepicker from "vue3-datepicker";
import 'vue3-datepicker/dist/vue3-datepicker.css';
import { format } from "date-fns";
import fr from "date-fns/locale/fr";
import en from "date-fns/locale/en-GB";

const locales = { fr, en };

export default {
  components: {
    Datepicker,
  },
  created() {
    this.locale = locales[config.lang];

    if (!this.value) return;

    this.dateRange.start = new Date(this.value.slice(0, 10));
    this.dateRange.end = new Date(this.value.slice(10));
  },
  props: {
    value: String,
    onChange: Function,
  },
  watch: {
    value: function (value) {
      //This allows to reset the value if the parent component decides to clear the value using the prop.
      if (typeof value === "undefined") {
        this.dateRange.start = null;
        this.dateRange.end = null;
      }
    },
  },
  data() {
    return {
      dateRange: {
        start: null,
        end: null,
      },
    };
  },
  methods: {
    _onChange: function () {
      if (!this.dateRange.start || !this.dateRange.end || !this.onChange)
        return;

      return this.onChange(
        format(this.dateRange.start, "yyyy-MM-dd") +
          "-" +
          format(this.dateRange.end, "yyyy-MM-dd")
      );
    },
  },
};
</script>
