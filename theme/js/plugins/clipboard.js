import copy from 'clipboard-copy';

export function install(Vue) {
    /**
     * Attach a tooltip on the element.
     */
    Vue.directive('clipboard', {
        bind() {
            this._copy = () => copy(this.expression);
            this.el.addEventListener('click', this._copy);
        },
        unbind() {
            this.el.removeEventListener('click', this._copy);
        },
        methods: {
            copy: (value) => copy(value),
        }
    });
}
