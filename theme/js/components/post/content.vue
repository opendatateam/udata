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
<div>
<box :title="post.name || ''" icon="newspaper-o"
    boxclass="box-solid post-content-widget">
    <image-button :src="post.image" :size="150"
        :endpoint="endpoint" :editable="$root.me.is_admin">
    </image-button>
    <p v-if="published"><strong>
        {{ _('Published on {date}', {date: published}) }}
    </strong></p>
    <p v-if="post.headline" class="lead">{{post.headline}}</p>
    <div v-markdown="post.content"></div>
</box>
</div>
</template>

<script>
import API from 'api';
import Box from 'components/containers/box.vue';
import ImageButton from 'components/widgets/image-button.vue';
import moment from 'moment';


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
        },
        published() {
            if (!this.post.published) return;
            return moment(this.post.published).format('LLL');
        }
    },
    events: {
        'image:saved': function() {
            this.post.fetch();
        }
    }
};
</script>
