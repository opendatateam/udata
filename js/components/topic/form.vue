<template>
<form-vertical v-ref:form fields="{{fields}}" model="{{topic}}"></form-vertical>
</template>

<script>
'use strict';

var Topic = require('models/topic');

module.exports = {
    props: ['topic'],
    data: function() {
        return {
            topic: new Topic(),
            fields: [{
                    id: 'name',
                    label: this._('Name')
                }, {
                    id: 'description',
                    label: this._('Description')
                }, {
                    id: 'tags',
                    label: this._('Tags'),
                    widget: 'tag-completer'
                }]
        };
    },
    components: {
        'form-vertical': require('components/form/vertical-form.vue')
    }
};
</script>
