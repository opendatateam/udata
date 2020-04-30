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
        let parsed = markdown(text);
        if (max_length) {
            // strip tags (not for sanitisation, done by markdown())
            parsed = parsed.replace(/(<([^>]+)>)/ig, '');
            return txt.truncate(parsed || '', max_length);
        } else {
            return parsed;
        }
    });
}
