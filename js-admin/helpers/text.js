define([], function() {
    'use strict';

    return {
        /**
         * Ellipsis a text given a length.
         * @param  {string} text   The text to truncate
         * @param  {int} length The truncate length
         * @return {string}        The truncated text
         */
        truncate: function(text, length) {
            if (text && text.length > length) {
                return text.substr(0, length - 3) + '...';
            }
            return text;
        },

        /**
         * Titleize a string
         * @param  {string} text  The input text to transform
         * @return {string}       The titleized string
         */
        title: function(text) {
            return text.replace(/\w\S*/g, function(txt) {
                return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
            });
        }
    };
});
