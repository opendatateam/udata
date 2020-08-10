import {ModelPage} from 'models/base';

export default class DatasetPage extends ModelPage {
    constructor(options) {
        super(options);
        this.$options.ns = 'datasets';
        this.$options.fetch = 'list_datasets';
    }
};
