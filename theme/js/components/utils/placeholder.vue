<!--
---
name: Placeholder
category: Interactions
---

# Placeholder

A very simple component that takes a `type` (dataset, reuse, post...) and an optionnal `src`. If `src` is defined, it simply displays the image (and all props passed are passed to the image).
However, if `src` is undefined, it falls back to a placeholder. Don't forget to pass the `alt` prop !
Sometimes you don't need an image but a `<div>` with a background-image property. Simply pass the `backgroundImage` prop and you will get a nice div.

-->

<template>
  <div
    v-if="backgroundImage"
    v-bind="$attrs"
    :style="{ backgroundImage: `url('${path}')` }"
  />
  <img :src="path" :alt="alternativeTextForDefinedImageOnly" v-bind="$attrs" v-else />
</template>

<script>
import config from "../../config";
const static = config.theme_static;

export const placeholderUrl = (src, type) =>
  src ? src : `${static}img/placeholders/${type}.png`;

export default {
  props: {
    type: String,
    src: String,
    alt: String,
    backgroundImage: Boolean,
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
