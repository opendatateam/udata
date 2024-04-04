<template>
<div class="page-header">
<h1>{{ _('Your reuse has been created') }}</h1>
</div>

<div class="row">
    <div class="col-xs-12 col-md-6 text-center">
        <button class="btn btn-primary btn-flat" v-link="'/reuse/'+reuse.id+'/'">
            {{ _('See in the administration') }}
        </button>
    </div>
    <div class="col-xs-12 col-md-6 text-center">
        <a class="btn btn-primary btn-flat" :href="reuse.page">
            {{ _('See on the site') }}
        </a>
    </div>
</div>
</template>

<script>
import Reuse from 'models/reuse';

export default {
    props: {
        reuse: {
            type: Object,
            default: function() {return {};}
        }
    },
    components: {}
};
</script>
