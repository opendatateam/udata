<template>
<box-container title="{{post.name}}" icon="building" boxclass="box-solid">
    <aside>
        <a class="text-muted pointer" v-on="click: toggle">
            <i class="fa fa-gear"></i>
        </a>
    </aside>
    <div v-if="!toggled">
        <p v-if="post.headline" class="lead">{{post.headline}}</p>
        <div v-markdown="{{post.content}}"></div>
    </div>
    <post-form v-ref="form" v-if="toggled" post="{{post}}"></post-form>
    <box-footer v-if="toggled">
        <button type="submit" class="btn btn-flat btn-primary"
            v-on="click: save($event)" v-i18n="Save"></button>
        <button type="button" class="btn btn-flat btn-warning"
            v-on="click: cancel($event)" v-i18n="Cancel"></button>
    </box-footer>
</box-container>
</template>

<script>
'use strict';

module.exports = {
    name: 'post-content',
    paramAttributes: ['post'],
    data: function() {
        return {
            toggled: false
        }
    },
    components: {
        'box-container': require('components/containers/box.vue'),
        'post-form': require('components/post/form.vue')
    },
    methods: {
        toggle: function() {
            this.toggled = !this.toggled;
        },
        save: function(e) {
            if (this.$.form.$.form.validate()) {
                var data = this.$.form.$.form.serialize();

                this.post.update(data);
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
