<template>
<form-vertical v-ref:form fields="{{fields}}" model="{{post}}"></form-vertical>
</template>

<script>
'use strict';

var Post = require('models/post');

module.exports = {
    props: ['post'],
    data: function() {
        return {
            post: new Post(),
            fields: [{
                    id: 'name',
                    label: this._('Name')
                }, {
                    id: 'headline',
                    label: this._('Headline')
                }, {
                    id: 'content',
                    label: this._('Content')
                }, {
                    id: 'tags',
                    label: this._('Tags'),
                    widget: 'tag-completer'
                }, {
                    id: 'private',
                    label: this._('Draft')
                }]
        };
    },
    components: {
        'form-vertical': require('components/form/vertical-form.vue')
    }
};
</script>
