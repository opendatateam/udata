<!-- Tag completer -->
<script>
import config from 'config';
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
        create(input) {
            return {
                value: input,
                text: input
            }
        },
        createFilter(value) {
            if (value) {
                return value.length >= config.tags.MIN_LENGTH && value.length <= config.tags.MAX_LENGTH;
            }
        }
    }
};
</script>
