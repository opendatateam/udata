<style lang="less">

</style>

<template>
<a class="pointer" v-on="click: click">
    <span class="fa fa-fw fa-exchange text-primary"></span>
    <span>{{ _('Pending transfer request') }}</span>
</a>
</template>

<script>
'use strict';

var Vue = require('vue');

module.exports = {
    mixins: [require('components/notifications/base')],
    methods: {
        click: function() {
            var m = this.$root.$modal({data: {
                            transferid: this.details.id
                        }
                    },
                    Vue.extend(require('components/transfer/response-modal.vue'))
                );
            // m.$once('transfer-to', function(type, recipient) {
            //     console.log('request transfer', type, recipient)
            //     this.dataset.transfer(type, recipient, 'test');
            //     this.dataset.$once('dataset:transfer:requested', function() {
            //         this.$dispatch('notify', {
            //             title: this._('Transfer requested'),
            //             details: this._('The recipient need to accept the transfer in order to complete it.')
            //         });
            //     }.bind(this));
            // }.bind(this));
            // this.$go('/organization/' + this.details.organization + '#membership-requests');
        }
    }
};
</script>
