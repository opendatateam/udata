import config from 'config';
import $ from 'jquery';
import commonmark from 'helpers/commonmark';
import txt from 'helpers/text';


export function install(Vue, options) {
    options = options || {};

    Vue.directive('markdown', {
        bind: function() {
            $(this.el).addClass('markdown');
        },
        update: function(value) {
            this.el.classList.add('markdown');
            this.el.innerHTML = value ? commonmark(value, config.markdown) : '';
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
            const div = document.createElement('div');
            div.classList.add('markdown');
            div.innerHTML = commonmark(text, config.markdown);
            return txt.truncate(div.textContent || div.innerText || '', max_length);
        } else {
            return commonmark(text, config.markdown);
        }
    });
}
