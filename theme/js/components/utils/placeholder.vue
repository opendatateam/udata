<!--
---
name: Placeholder
category: Interactions
---

# Placeholder

A very simple component that takes a `type` (dataset, reuse, post...) and an optionnal `src`. If `src` is defined, it simply displays the image (and all props passed are passed to the image).
However, if `src` is undefined, it falls back to a placeholder. Don't forget to pass the `alt` prop !

-->

<template>
    <img :src="path" :alt="alt" v-bind="$attrs" />
</template>

<script>
import config from "../../config";

export default {
    props: {
        type: String,
        src: String,
        alt: String
    },
    data() {
        return {
            static: config.theme_static
        }
    },
    computed: {
        path() {
            if(this.src)
                return src;
            return `${this.static}img/placeholders/${this.type}.png`
        }
    }
}
</script>
