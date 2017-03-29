<template>
<a class="avatar" :href="user.url" :title="user | display">
    <img class="avatar" :src="url"
        :alt="user | display" :width="size" :height="size">
</a>
</template>

<script>
import placeholders from 'helpers/placeholders';

const DEFAULT_SIZE = 52;

export default {
    props: {
        user: Object,
        size: {
            type: Number,
            default: DEFAULT_SIZE
        }
    },
    computed: {
        url() {
            return this.user.avatar_thumbnail || this.user.avatar || placeholders.user;
        }
    }
}
</script>
