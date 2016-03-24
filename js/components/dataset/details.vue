<template>
<box :title="_('Details')" icon="cubes" boxclass="box-solid">
    <h3>{{dataset.title}}</h3>
    <div v-markdown="dataset.description"></div>
    <div v-if="dataset.tags | length" class="label-list">
        <strong>
            <span class="fa fa-fw fa-tags"></span>
            {{ _('Tags') }}:
        </strong>
        <span v-for="tag in dataset.tags" class="label label-default">{{tag}}</span>
    </div>
    <div v-if="dataset.badges | length" class="label-list">
        <strong>
            <span class="fa fa-fw fa-bookmark"></span>
            {{ _('Badges') }}:
        </strong>
        <span v-for="b in dataset.badges" class="label label-primary">{{badges[b.kind]}}</span>
    </div>
</box>
</template>

<script>
import Box from 'components/containers/box.vue';
import badges from 'models/badges';

export default {
    name: 'dataset-details',
    props: ['dataset'],
    data: function() {
        return {
            badges: badges.dataset
        };
    },
    components: {Box}
};
</script>
