<template>
<div class="page-header">
<h1>{{ _('Your community resource has been created') }}</h1>
</div>

<div class="row">
    <div class="col-xs-12 lead text-center">
        <a class="btn btn-primary btn-flat" :href="communityResource.url">
            {{ _('See on the site') }}
        </a>
    </div>
</div>
</template>

<script>
import CommunityResource from 'models/communityresource';

export default {
    props: {
        communityResource: {
            type: Object,
            default() {return new CommunityResource();}
        }
    },
    components: {}
};
</script>
