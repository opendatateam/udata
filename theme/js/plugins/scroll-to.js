import velocity from 'velocity-animate';

export function install(Vue) {
    /**
     * Fetch an element given its selector.
     * Pass through if it's already an element
     * @param  {Element|Vue|String} target The target element to find
     * @return {Element}        The real matching element
     */
    function resolve(target) {
        if (target instanceof Element) return target;
        if (target instanceof Vue) return target.$el;
        return document.querySelector(target);
    }

    /**
     * Scroll to the top of given element
     */
    Vue.prototype.$scrollTo = Vue.scrollTo = function(target) {
        const el = resolve(target);
        velocity(el, 'scroll', {duration: 500});
    };
}
