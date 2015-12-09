<template>
<div class="page-header">
  <h1>{{ _('Your dataset has been created') }}</h1>
</div>
<div class="row">
    <div class="col-xs-12 lead text-center">
        <p>{{ _('You should communicate about it.') }}</p>
    </div>
</div>
<share :url="dataset.page" :title="dataset.title"></share>

<div class="row">
    <div class="col-xs-12 col-md-6 text-center">
        <button class="btn btn-primary btn-flat" v-link="{name: 'dataset', params: {oid: dataset.id}}">
            {{ _('See in the administration') }}
        </button>
    </div>
    <div class="col-xs-12 col-md-6 text-center">
        <a class="btn btn-primary btn-flat" :href="dataset.page">
            {{ _('See on the site') }}
        </a>
    </div>
</div>
</template>

<script>
export default {
    props: {
        dataset: {
            type: Object,
            default: function() {
                return {};
            }
        }
    },
    components: {
        share: require('components/widgets/share.vue')
    }
};
</script>
