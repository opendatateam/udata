<template>
<div class="page-header">
  <h1>{{ _('Your harvester has been created') }}</h1>
</div>
<div class="row">
    <div class="col-xs-12 lead text-center">
        <p>{{ _('Your harvester is now pending for team review.') }}</p>
        <p>{{ _("You'll be notified on approval (or refusal)") }}</p>
    </div>
</div>

<div class="row">
    <div class="col-xs-12 col-md-6 text-center">
        <button class="btn btn-primary btn-flat"
            v-link="{name: 'harvester', params: {oid: source.id}}">
            {{ _('See in the administration') }}
        </button>
    </div>
</div>
</template>

<script>
export default {
    data: function() {
        return {source: {}};
    },
    props: ['source']
};
</script>
