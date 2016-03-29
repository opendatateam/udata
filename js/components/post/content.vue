<style lang="less">
.post-content-widget {
    .image-button {
        border: 1px solid darken(white, 20%);
        float: left;
        margin: 0 10px 5px 0;
    }

    .box-body {
        h3 {
            margin-top: 0;
        }
    }
}
</style>
<template>
<box :title="post.name || ''" icon="newspaper-o"
    boxclass="box-solid post-content-widget">
    <image-button :src="post.image" :size="150"
        :endpoint="endpoint">
    </image-button>
    <p v-if="post.headline" class="lead">{{post.headline}}</p>
    <div v-markdown="post.content"></div>
</box>
</template>

<script>
import API from 'api';
import Box from 'components/containers/box.vue';
import ImageButton from 'components/widgets/image-button.vue';

export default {
    name: 'post-content',
    props: {
        post: Object,
        required: true
    },
    data() {
        return {
            toggled: false
        }
    },
    components: {Box, ImageButton},
    computed: {
        endpoint() {
            if (this.post.id) {
                var operation = API.posts.operations.post_image;
                return operation.urlify({post: this.post.id});
            }
        }
    },
    events: {
        'image:saved': function() {
            this.post.fetch();
        }
    }
};
</script>
