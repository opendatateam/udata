<style lang="less">
.datatable {
    td.ellipsis {
        white-space: nowrap;
        overflow: hidden;
        text-overflow:ellipsis;
        max-width: 0;
    }
}
</style>

<script>
import Vue from 'vue';
import utils from 'utils';

export default {
    name: 'datatable-cell',
    default: '',
    replace: true,
    props: {
        field: Object,
        item: Object
    },
    computed: {
        value: function() {
            if (!this.field || !this.item) {
                return this.$options.default;
            }

            if (utils.isFunction(this.field.key)) {
                result = this.field.key(this.item);
            } else {
                var parts = this.field.key.split('.'),
                    result = this.item;

                for (var i=0; i < parts.length; i++) {
                    var key = parts[i];
                    if (!result || !result.hasOwnProperty(key)) {
                        result = null;
                        break;
                    }
                    result = result[key];
                }
            }

            return result || this.$options.default;
        }
    }
};
</script>
