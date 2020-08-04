<template>
<div class="page-header">
  <h1>{{ _('Your organization has been created') }}</h1>
</div>
<div class="row">
    <div class="col-xs-12 lead text-center">
        <p>{{ _('You can now either publish a dataset or a reuse.') }}</p>
    </div>
</div>
<div class="row">
    <div class="col-xs-12 col-md-4 text-center">
        <button class="btn btn-primary btn-flat" v-link.literal="/dataset/new/">
            {{ _('Publish a new dataset') }}
        </button>
    </div>
    <div class="col-xs-12 col-md-4 text-center">
        <button class="btn btn-primary btn-flat" v-link.literal="/reuse/new/">
            {{ _('Publish a new reuse') }}
        </button>
    </div>
    <div class="col-xs-12 col-md-4 text-center">
        <button class="btn btn-primary btn-flat"
            v-link="'/organization/' + organization.id + '/'">
            {{ _('See in the administration') }}
        </button>
    </div>
</div>
</template>

<script>
export default {
    props: {
        organization: {
            type: Object,
            default: function() {return {};}
        }
    }
};
</script>
