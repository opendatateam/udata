<template>
<div class="territory-popup">
    <b>{{feature.properties.name}}</b>
    <br/>
    <a :href="url">{{ _('n_datasets', {count: feature.properties.datasets}) }}</a>
    <a class="drill-down" v-for="child in children" @click.prevent="$dispatch('drillDown', child, bounds)">
        <span class="fa fa fa-arrow-circle-down"></span>
        {{ child.name }}
    </a>
</div>
</template>

<script>
export default {
    props: {
        feature: Object,
        children: Array,
        bounds: Object,
    },
    computed: {
        url() {
            return `/datasets?geozone=${this.feature.id}`;
        }
    }
};
</script>
<style lang="less">
.territory-popup {
    .drill-down {
        display: block;
        cursor: pointer;
    }
}
</style>
