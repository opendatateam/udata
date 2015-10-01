import DatasetPage from 'models/datasets';

export default class DatasetFullPage extends DatasetPage {
    constructor(options) {
        super(options);
        this.$options.fetch = 'list_datasets_full';
    }
};
