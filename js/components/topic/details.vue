<template>
<box-container title="{{topic.name}}" icon="building" boxclass="box-solid">
    <aside>
        <a class="text-muted pointer" @click="toggle">
            <i class="fa fa-gear"></i>
        </a>
    </aside>
    <div v-if="!toggled">
        <div :v-markdown="topic.description"></div>
    </div>
    <topic-form v-ref:form v-if="toggled" topic="{{topic}}"></topic-form>
    <box-footer v-if="toggled">
        <button type="submit" class="btn btn-flat btn-primary"
            @click="save($event)" v-i18n="Save"></button>
        <button type="button" class="btn btn-flat btn-warning"
            @click="cancel($event)" v-i18n="Cancel"></button>
    </box-footer>
</box-container>
</template>

<script>
'use strict';

module.exports = {
    name: 'topic-content',
    props: ['topic'],
    data: function() {
        return {
            toggled: false
        }
    },
    components: {
        'box-container': require('components/containers/box.vue'),
        'topic-form': require('components/topic/form.vue')
    },
    methods: {
        toggle: function() {
            this.toggled = !this.toggled;
        },
        save: function(e) {
            if (this.$refs.form.$.form.validate()) {
                var data = this.$refs.form.$.form.serialize();

                this.topic.save(data);
                e.preventDefault();

                this.toggled = false;
            }
        },
        cancel: function(e) {
            this.toggled = false;
        }
    }
};
</script>
