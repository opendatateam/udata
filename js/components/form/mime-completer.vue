<!-- MIME type autocompleter -->
<script>
import Vue from 'vue';
import API from 'api';
import BaseCompleter from 'components/form/base-completer.vue';

export default {
    mixins: [BaseCompleter],
    ns: 'datasets',
    endpoint: 'suggest_mime',
    selectize: {
        maxItems: 1,
        valueField: 'text',
        create(input) {
            return {
                value: input,
                text: input
            }
        }
    }
};
</script>
