<!-- Formats autocompleter -->
<script>
import BaseCompleter from 'components/form/base-completer.vue';

export default {
    mixins: [BaseCompleter],
    ns: 'datasets',
    endpoint: 'suggest_formats',
    selectize: {
        maxItems: 1,
        valueField: 'text',
        create: function(input) {
            return {
                value: input,
                text: input
            }
        }
    }
};
</script>
