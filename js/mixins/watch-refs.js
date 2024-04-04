/**
 * A mixin to workaround the $refs lack of reactivity
 */
export default {
    ready() {
        for (const $ref of Object.keys(this.$options.watchRefs)) {
            this.watchRef($ref, this.$options.watchRefs[$ref]);
        }
    },
    methods: {
        watchRef($ref, handler) {
            const component = $ref.split('.')[0];

            const wait = () => { // Arrow func to keep `this`
                if (this.$refs[component] === undefined) {
                    setTimeout(wait, 1);
                    return;
                }
                this.$watch(`$refs.${$ref}`, handler.bind(this));
            };
            wait();
        }
    }
}
