import text from 'helpers/text';

export function install(Vue) {
    /**
     * Ellipsis a text given a length.
     * @param  {string} text   The text to truncate
     * @param  {int} length The truncate length
     * @return {string}        The truncated text
     */
    Vue.filter('truncate', text.truncate);

    /**
     * Titleize a string
     * @param  {string} text  The input text to transform
     * @return {string}       The titleized string
     */
    Vue.filter('title', text.title);

    /**
     * Join an array
     */
    Vue.filter('join', function(value, separator) {
        if (Array.isArray(value)) {
            return value.join(separator || '');
        }
        return value;
    });

    /**
     * Lower a text case
     */
    Vue.filter('lower', function(value) {
        return (value || '').toLowerCase();
    });

    /**
     * Display a bytes size in a human readable format
     */
    Vue.filter('size', text.size);

    /**
     * More readable numbers
     */
    Vue.filter('numbers', function(value) {
        return (value || 0).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    });
}
