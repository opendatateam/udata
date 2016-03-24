<template>
<box :title="topic.name || ''" icon="book" boxclass="box-solid">
    <div v-markdown="topic.description"></div>
    <div v-if="topic.tags | length" class="label-list">
        <strong>
            <span class="fa fa-fw fa-tags"></span>
            {{ _('Tags') }}:
        </strong>
        <span v-for="tag in topic.tags" class="label label-default">{{tag}}</span>
    </div>
</box>
</template>

<script>
import Box from 'components/containers/box.vue';

export default {
    name: 'topic-content',
    props: ['topic'],
    components: {Box}
};
</script>
