<style lang="less">

</style>

<template>
<form-horizontal class="resource-form remote-resource-form"
        fields="{{fields}}" model="{{resource}}" v-ref="form">
</form-horizontal>
</template>

<script>
'use strict';

module.exports = {
    inherit: true,
    data: function() {
        return {
            fields: [{
                    id: 'title',
                    label: this._('Title')
                }, {
                    id: 'description',
                    label: this._('Description'),
                }, {
                    id: 'url',
                    label: this._('URL'),
                }, {
                    id: 'size',
                    label: this._('Size'),
                }, {
                    id: 'format',
                    label: this._('Format'),
                    widget: 'format-completer'
                }, {
                    id: 'mime',
                    label: this._('Mime Type'),
                }, {
                    id: 'checksum',
                    label: this._('Checksum'),
                    widget: 'checksum'
                }]
        };
    },
    components: {
        'form-horizontal': require('components/form/horizontal-form.vue')
    },
};
</script>
