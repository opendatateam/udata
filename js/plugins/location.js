import {parseQS} from 'utils';

/**
 * Expose and parse window.location
 */
export class Location {
    constructor() {
        this.parse();
    }

    /**
     * Parse location
     *
     * Extracted from constructor to allow reparse on history popstate
     */
    parse() {
        this.query = parseQS(window.location.search);
    }
}


export function install(Vue) {
    // Tha wrapper is accessible on Vue.location or this.$location on instances
    Vue.prototype.$location = Vue.location = new Location();
}
