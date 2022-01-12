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
      <strong class="text-grey-380 f-normal mr-xxs">{{ $t("from") }}</strong>
      <div class="datepicker">
        <Datepicker
          v-model="dateRange.start"
          :upperLimit="dateRange.end"
          @update:modelValue="_onChange"
          placeholder="__/__/__"
          :locale="locale"
        />
        <span
          class="clear"
          @click="clear"
          v-html="closeIcon"
          v-if="dateRange.start"
        />
      </div>
    </div>
    <div class="row-inline align-items-center">
      <strong class="text-grey-380 f-normal mr-xxs ml-xs">{{
        $t("to")
      }}</strong>
      <div class="datepicker">
        <Datepicker
          v-model="dateRange.end"
          :lowerLimit="dateRange.start"
          @update:modelValue="_onChange"
          placeholder="__/__/__"
          :locale="locale"
        />
        <span
          class="clear"
          @click="clear"
          v-html="closeIcon"
          v-if="dateRange.end"
        />
      </div>
    </div>
  </div>
</template>

<script>
import config from "../../config";
import Datepicker from "vue3-datepicker";
import "vue3-datepicker/dist/vue3-datepicker.css";
import closeIcon from "svg/close.svg";
import { format } from "date-fns";
import fr from "date-fns/locale/fr";
import en from "date-fns/locale/en-GB";
import es from "date-fns/locale/es";

const locales = { fr, en, es };

export default {
  components: {
    Datepicker,
  },
  created() {
    this.closeIcon = closeIcon;
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
      if (!this.onChange) return;

      let value = null;

      if (this.dateRange.start && this.dateRange.end)
        value =
          format(this.dateRange.start, "yyyy-MM-dd") +
          "-" +
          format(this.dateRange.end, "yyyy-MM-dd");

      return this.onChange(value);
    },
    clear: function () {
      this.dateRange.start = null;
      this.dateRange.end = null;

      this._onChange();
    },
  },
};
</script>
