import {ModelPage} from 'models/base';

export default class SiteActivityPage extends ModelPage {
    constructor(options) {
        super(options);
        this.$options.ns = 'site';
        this.$options.fetch = 'site_activity';
    }
};

export var activities = new SiteActivityPage().fetch();
export default activities;
