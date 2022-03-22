<!--
---
name: Read More
category: 5 - Interactions
---

# Read More

A very simple component that display its content up to a maximum height and then add a "read more" link.

-->

<template>
  <div ref="container" class="read-more" :class="{expand: expanded}" :style="{height: containerHeight + 'px'}">
    <slot></slot>
    <a href="#" @click.prevent="toggle" v-if="readMoreRequired" class="read-more-link">
      <template v-if="expanded"> {{ $t("Read less") }}</template>
      <template v-else>{{ $t("Read more") }}&hellip;</template>
    </a>
  </div>
</template>

<script>
import { easing, tween, styler } from "popmotion";

function getHeight(elt) {
  const style = getComputedStyle(elt);
  return parseFloat(style.getPropertyValue('height')) +
    parseFloat(style.getPropertyValue('margin-top')) +
    parseFloat(style.getPropertyValue('margin-bottom'));
}

const DEFAULT_HEIGHT = 284;

export default {
  name: "read-more",
  data() {
    return {
      containerHeight: DEFAULT_HEIGHT,
      expanded: false,
      readMoreRequired: false,
    }
  },
  mounted() {
    this.updateReadMoreHeight();
    setTimeout(() => this.updateReadMoreHeight(), 500);
  },
  methods: {
    toggle() {
      this.expanded = !this.expanded;
      const divStyler = styler(this.$refs.container);
      if (this.expanded) {
            tween({
              from: { height: DEFAULT_HEIGHT },
              to: { height: this.$refs.container.scrollHeight },
              duration: 300,
              ease: easing.anticipate,
            }).start({
              update: divStyler.set,
              complete: () => divStyler.set({ height: "auto" }),
            });
          } else {
            tween({
              from: { height: this.$refs.container.scrollHeight },
              to: { height: DEFAULT_HEIGHT },
              duration: 300,
              ease: easing.anticipate,
            }).start(divStyler.set);
          }
    },
    updateReadMoreHeight() {
      let contentHeight = Array.from(this.$refs.container.children)
      .map(getHeight)
      .reduce((total, height) => total + height, 0)
      this.containerHeight = DEFAULT_HEIGHT;
      this.readMoreRequired = contentHeight > this.containerHeight;
      if(!this.readMoreRequired) {
        this.containerHeight = contentHeight;
      }
    }
  }
}
</script>
