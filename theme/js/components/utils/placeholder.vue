<!--
---
name: Placeholder
category: 5 - Interactions
---

# Placeholder

A very simple component that takes a `type` (dataset, reuse, post...) and an optional `src`. If `src` is defined, it simply displays the image (and all props passed are passed to the image).
However, if `src` is undefined, it falls back to a placeholder. Don't forget to pass the `alt` prop !

-->

<template>
  <img
    loading="lazy"
    :src="path"
    :alt="alternativeTextForDefinedImageOnly"
    :width="size"
    :height="size"
    v-bind="$attrs"
  />
</template>

<script>
import config from "../../config";

export const placeholderUrl = (src, type) =>
  src ? src : `${config.theme_static}img/placeholders/${type}.png`;

export default {
  props: {
    type: String,
    src: String,
    alt: String,
    size: Number,
  },
  computed: {
    alternativeTextForDefinedImageOnly() {
      return this.src ? this.alt : '';
    },
    path() {
      return placeholderUrl(this.src, this.type);
    },
  },
};
</script>
