<template>
<a class="avatar" :href="user.url" :title="user | display">
    <img class="avatar" :src="user | avatar_url size"
        :alt="user | display" :width="size" :height="size">
</a>
</template>

<script>

const DEFAULT_SIZE = 52;

export default {
    props: {
        user: Object,
        size: {
            type: Number,
            default: DEFAULT_SIZE
        }
    }
}
</script>
