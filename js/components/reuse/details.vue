<style lang="less">
.reuse-details-widget {
    .thumbnail-button {
        border: 1px solid darken(white, 20%);
        float: left;
        margin: 0 10px 5px 0;
    }

    .box-body {
        h3 {
            margin-top: 0;
        }
    }

    .details-body {
        min-height: 100px;
    }
}
</style>

<template>
<div>
<box :title="_('Details')" icon="recycle" boxclass="box-solid reuse-details-widget">
    <h3>{{reuse.title}}</h3>
    <div class="details-body">
        <image-button :src="reuse.image_thumbnail" :size="100" class="thumbnail-button"
            :endpoint="endpoint" :editable="$root.me.can_edit(reuse)">
        </image-button>
        <div v-markdown="reuse.description"></div>
        <div v-if="reuse.tags" class="label-list">
            <strong>
                <span class="fa fa-fw fa-tags"></span>
                {{ _('Tags') }}:
            </strong>
            <span v-for="tag in reuse.tags" class="label label-default">{{tag}}</span>
        </div>
        <div v-if="reuse.badges | length" class="label-list">
            <strong>
                <span class="fa fa-fw fa-bookmark"></span>
                {{ _('Badges') }}:
            </strong>
            <span v-for="b in reuse.badges" class="label label-primary">{{badges[b.kind]}}</span>
        </div>
    </div>
</box>
</div>
</template>

<script>
import API from 'api';
import Box from 'components/containers/box.vue';
import ImageButton from 'components/widgets/image-button.vue';

export default {
    name: 'reuse-details',
    components: {Box, ImageButton},
    props: ['reuse'],
    data() {
        return {
            badges: require('models/badges').badges.reuse
        };
    },
    computed: {
        endpoint() {
            if (this.reuse.id) {
                var operation = API.reuses.operations.reuse_image;
                return operation.urlify({reuse: this.reuse.id});
            }
        }
    },
    events: {
        'image:saved': function() {
            this.reuse.fetch();
        }
    },
};
</script>
