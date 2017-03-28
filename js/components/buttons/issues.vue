<template>
<button type="button" class="btn btn-danger btn-issues" @click="click"
    v-tooltip tooltip-placement="top" :title="_('Issues')">
    <span class="fa fa-warning"></span>
    <span v-if="count" class="count">{{ count }}</span>
</button>
</template>

<script>
import ObjectIssuesModal from 'components/issues/object-modal.vue';

export default {
    props: {
        subjectId: {
            type: String,
            required: true,
        },
        subjectClass: {
            type: String,
            required: true,
        },
        count: {
            type: Number,
            default: 0,
            coerce: parseInt
        }
    },
    methods: {
        click() {
            this.$root.$modal(ObjectIssuesModal, {subject: {id: this.subjectId, class: this.subjectClass}});
        }
    }
};
</script>

<style lang="less"></style>
