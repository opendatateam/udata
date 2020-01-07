import $ from 'jquery';
import markdown from 'helpers/markdown';
import txt from 'helpers/text';


export function install(Vue, options) {
    options = options || {};

    Vue.directive('markdown', {
        bind: function() {
            $(this.el).addClass('markdown');
        },
        update: function(value) {
            this.el.classList.add('markdown');
            this.el.innerHTML = value ? markdown(value) : '';
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
            div.innerHTML = markdown(text);
            return txt.truncate(div.textContent || div.innerText || '', max_length);
        } else {
            return markdown(text);
        }
    });
}
