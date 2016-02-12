<template>
<box :title="topic.name || ''" icon="building" boxclass="box-solid"
    :footer="toggled">
    <aside slot="tools">
        <a class="text-muted pointer" @click="toggle">
            <i class="fa fa-gear"></i>
        </a>
    </aside>
    <div v-if="!toggled">
        <div v-markdown="topic.description"></div>
    </div>
    <topic-form v-ref:form v-if="toggled" :topic="topic"></topic-form>
    <footer v-if="toggled" slot="footer">
        <button type="submit" class="btn btn-flat btn-primary"
            @click="save($event)" v-i18n="Save"></button>
        <button type="button" class="btn btn-flat btn-warning"
            @click="cancel($event)" v-i18n="Cancel"></button>
    </footer>
</box>
</template>

<script>
export default {
    name: 'topic-content',
    props: ['topic'],
    data: function() {
        return {
            toggled: false
        }
    },
    components: {
        box: require('components/containers/box.vue'),
        'topic-form': require('components/topic/form.vue')
    },
    methods: {
        toggle: function() {
            this.toggled = !this.toggled;
        },
        save: function(e) {
            const form = this.$refs.form.$refs.form;
            if (form.validate()) {
                e.preventDefault();
                this.topic.update(form.serialize(), (response) => {
                    this.topic.on_fetched(response);
                    this.toggled = false;
                }, form.on_error);
            }
        },
        cancel: function(e) {
            this.toggled = false;
        }
    }
};
</script>
