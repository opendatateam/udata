<style lang="less">

</style>

<template>
<div class="page-header">
  <h1>{{ _('Your reuse has been created') }}</h1>
</div>
<div class="row">
    <div class="col-xs-12 lead text-center">
        <p>{{ _('You should communicate about it.') }}</p>
    </div>
</div>
<share-widget url="{{reuse.page}}" title="{{reuse.title}}"></share-widget>

<div class="row">
    <div class="col-xs-12 col-md-6 text-center">
        <button class="btn btn-primary btn-flat" v-route="/reuse/{{reuse.id}}/">
            {{ _('See in the administration') }}
        </button>
    </div>
    <div class="col-xs-12 col-md-6 text-center">
        <a class="btn btn-primary btn-flat" href="{{reuse.page}}">
            {{ _('See on the site') }}
        </a>
    </div>
</div>
</template>

<script>
'use strict';

var Reuse = require('models/reuse');

module.exports = {
    props: ['reuse'],
    data: function() {
        return {reuse: {}};
    },
    components: {
        'share-widget': require('components/widgets/share.vue')
    },
    // watch: {
    //     'reuse.id': function(id, old_id) {
    //         console.log(id, old_id);
    //         if (id !== old_id) {
    //             this.$emit('reuse:updated');
    //         }
    //     }
    // }
};
</script>
