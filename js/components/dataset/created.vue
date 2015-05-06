<style lang="less">

</style>

<template>
<div class="page-header">
  <h1>{{ _('Your dataset has been created') }}</h1>
</div>
<div class="row">
    <div class="col-xs-12 lead text-center">
        <p>{{ _('You should communicate about it.') }}</p>
    </div>
</div>
<share-widget url="{{dataset.page}}" title="{{dataset.title}}"></share-widget>

<div class="row">
    <div class="col-xs-12 col-md-6 text-center">
        <button class="btn btn-primary btn-flat" v-route="/dataset/{{dataset.id}}/">
            {{ _('See in the administration') }}
        </button>
    </div>
    <div class="col-xs-12 col-md-6 text-center">
        <a class="btn btn-primary btn-flat" href="{{dataset.page}}">
            {{ _('See on the site') }}
        </a>
    </div>
</div>
</template>

<script>
'use strict';

module.exports = {
    data: function() {
        return {dataset: {}};
    },
    paramAttributes: ['dataset'],
    components: {
        'share-widget': require('components/widgets/share.vue')
    }
};
</script>
