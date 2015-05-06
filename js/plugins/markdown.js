define(['jquery', 'marked', 'helpers/text'], function($, marked, txt) {
    'use strict';

    return function(Vue, options) {
        options = options || {};

        Vue.directive('markdown', {
            isLiteral: true,
            bind: function() {
                $(this.el).addClass('markdown');
            },
            update: function(value) {
                this.el.innerHTML = value ? marked(value) : '';
            },
            unbind: function() {
                $(this.el).removeClass('markdown');
            },
        });

        Vue.filter('markdown', function(text, max_length) {
            if (!text) {
                return '';
            }
            if (max_length) {
                var div = document.createElement("div");
                div.innerHTML = marked(text);
                return txt.truncate(div.textContent || div.innerText || '', max_length);
            } else {
                return marked(text);
            }
        });
    };
});


