<template>
<button type="button" class="btn btn-primary btn-share" :title="_('Share')" v-tooltip
    v-popover popover-large :popover-title="_('Share')">
    <span class="fa fa-share-alt"></span>
    <div class="btn-group btn-group-lg" slot="content" v-popover-content>
        <a class="btn btn-link" title="Google+" @click="click"
            href="https://plus.google.com/share?url={{url|encode}}" target="_blank">
            <span class="fa fa-2x fa-google-plus"></span>
        </a>
        <a class="btn btn-link" title="Twitter" @click="click"
            href="https://twitter.com/home?status={{title|encode}}%20-%20{{url|encode}}" target="_blank">
            <span class="fa fa-2x fa-twitter"></span>
        </a>
        <a class="btn btn-link" title="Facebook" @click="click"
            href="https://www.facebook.com/sharer/sharer.php?u={{url|encode}}" target="_blank">
            <span class="fa fa-2x fa-facebook"></span>
        </a>
        <a class="btn btn-link" title="LinkedIn" @click="click"
            href="https://www.linkedin.com/shareArticle?mini=true&url={{url|encode}}&title={{title|encode}}" target="_blank">
            <span class="fa fa-2x fa-linkedin"></span>
        </a>
    </div>
</button>
</template>
<script>
import i18n from 'i18n';
import pubsub from 'pubsub';

export default {
    props: {
        title: {
            type: String,
            required: true
        },
        url: {
            type: String,
            required: true
        }
    },
    filters: {
        encode: encodeURIComponent
    },
    methods: {
        click() {
            pubsub.publish('SHARE');
            this.$refs.popover.show = false;
        }
    }
};
</script>
<style lang="less">

</style>
