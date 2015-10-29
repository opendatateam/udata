<style lang="less">

</style>

<template>
<!--div v-form="dataset" v-fields="fields"></div-->
<form-vertical v-ref:form fields="{{fields}}" model="{{dataset}}"></form-vertical>
</template>

<script>
'use strict';

module.exports = {
    props: ['dataset'],
    data: function() {
        return {
            fields: ['title', 'description']
            // fields: [{
            //         id: 'title',
            //         label: this._('Title')
            //     }, {
            //         id: 'description',
            //         type: 'markdown',
            //         label: this._('Description'),
            //     }]
        };
    },
    components: {
        'form-vertical': require('components/form/vertical-form.vue')
    }
};
</script>
