import {ModelPage} from 'models/base';


export default class HarvestSourcePage extends ModelPage {
    constructor(options) {
        super(options);
        this.$options.ns = 'harvest';
        this.$options.fetch = 'list_harvest_sources';
    }
};
