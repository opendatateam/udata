<template>
<div class="row">
    <div class="col-xs-12 text-center">
        <div class="btn-group btn-group-lg">
            <a class="btn btn-link" title="Google+"
                :href="google" target="_blank">
                <span class="fa fa-2x fa-google-plus"></span>
            </a>
            <a class="btn btn-link" title="Twitter"
                :href="twitter" target="_blank">
                <span class="fa fa-2x fa-twitter"></span>
            </a>
            <a class="btn btn-link" title="Facebook"
                :href="facebook" target="_blank">
                <span class="fa fa-2x fa-facebook"></span>
            </a>
            <a class="btn btn-link" title="LinkedIn"
                :href="linkedin" target="_blank">
                <span class="fa fa-2x fa-linkedin"></span>
            </a>
        </div>
    </div>
</div>
</template>

<script>
export default {
    props: ['title', 'url'],
    computed: {
        google() {
            return `https://plus.google.com/share?url=${this.url}`;
        },
        twitter() {
            return `https://twitter.com/home?status=${this.title}%20-%20${this.url}`;
        },
        facebook() {
            return `https://www.facebook.com/sharer/sharer.php?u=${this.url}`;
        },
        linkedin() {
            return `https://www.linkedin.com/shareArticle?mini=true&url=${this.url}&title=${this.title}`;
        }
    }
};
</script>
