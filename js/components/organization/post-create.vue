<style lang="less">

</style>

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
    <div class="col-xs-12 col-md-6 text-center">
        <button class="btn btn-primary btn-flat" v-route="/dataset/new/">
            {{ _('Publish a new dataset') }}
        </button>
    </div>
    <div class="col-xs-12 col-md-6 text-center">
        <button class="btn btn-primary btn-flat" v-route="/reuse/new/">
            {{ _('Publish a new reuse') }}
        </button>
    </div>
</div>
</template>

<script>
'use strict';

module.exports = {
    data: function() {
        return {};
    }
};
</script>
