/**
 * Common boostrap modal behavior
 */
define(['jquery'], function($) {
    'use strict';

    function $el(vm) {
        return $(vm.$el).hasClass('modal') ? $(vm.$el) : vm.$find('.modal');
    }

    return {
        events: {
            'modal:close': function() {
                this.hide();
            }
        },
        ready: function() {
            $el(this).modal().on('hidden.bs.modal', function() {
                this.$destroy(true);
            }.bind(this));
        },
        methods: {
            hide: function() {
                $el(this).modal('hide');
            }
        }
    }

});
