 import $ from 'jquery';

/**
 * Common boostrap modal behavior
 */
export default {
     ready: function() {
         $(this.$el).modal()
             .on('hide.bs.modal', (e) => {
                 this.$dispatch('modal:close');
             })
             .on('hidden.bs.modal', () => {
                 this.$dispatch('modal:closed');
                 this.$destroy(true);
             });
     },
     methods: {
         close: function() {
             $(this.$el).modal('hide');
         }
     }
 };
