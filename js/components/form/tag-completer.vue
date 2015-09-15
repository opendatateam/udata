<!-- Tag completer -->
<script>
import Vue from 'vue';
import API from 'api';
import BaseCompleter from 'components/form/base-completer.vue';

export default {
    mixins: [BaseCompleter],
    ns: 'tags',
    endpoint: 'suggest_tags',
    selectize: {
        valueField: 'text',
        plugins: ['remove_button'],
        create: function(input) {
            return {
                value: input,
                text: input
            }
        }
    }
};
</script>
