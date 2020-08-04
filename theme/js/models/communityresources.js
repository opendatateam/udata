import {ModelPage} from 'models/base';

export default class CommunityResourcePage extends ModelPage {
    constructor(options) {
        super(options);
        this.$options.ns = 'datasets';
        this.$options.fetch = 'list_community_resources';
    }
};
