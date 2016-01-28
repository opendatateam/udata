import $ from 'jquery';

export function install(Vue) {  // jshint ignore:line
    Vue.prototype.$scrollTo = Vue.scrollTo = function(target) {
        $('html, body').animate({
            scrollTop: $(target).offset().top - $('.main-header').height() - 5
        }, 600);
    };
}
