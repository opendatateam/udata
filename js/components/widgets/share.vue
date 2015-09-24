<template>
<div class="row">
    <div class="col-xs-12 text-center">
        <div class="btn-group btn-group-lg">
            <a class="btn btn-link" title="Google+"
                href="https://plus.google.com/share?url={{url}}" target="_blank">
                <span class="fa fa-2x fa-google-plus"></span>
            </a>
            <a class="btn btn-link" title="Twitter"
                href="https://twitter.com/home?status={{title}}%20-%20{{url}}" target="_blank">
                <span class="fa fa-2x fa-twitter"></span>
            </a>
            <a class="btn btn-link" title="Facebook"
                href="https://www.facebook.com/sharer/sharer.php?u={{url}}" target="_blank">
                <span class="fa fa-2x fa-facebook"></span>
            </a>
            <a class="btn btn-link" title="LinkedIn"
                href="https://www.linkedin.com/shareArticle?mini=true&url={{url}}&title={{title}}" target="_blank">
                <span class="fa fa-2x fa-linkedin"></span>
            </a>
        </div>
    </div>
</div>
</template>

<script>
export default {
    props: ['title', 'url']
};
</script>
