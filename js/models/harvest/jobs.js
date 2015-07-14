import {ModelPage} from 'models/base';
import log from 'logger';


export default class HarvestJobPage extends ModelPage {
    constructor(options) {
        super(options);
        this.$options.ns = 'harvest';
        this.$options.fetch = 'list_harvest_jobs';
    }
};
