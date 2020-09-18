import {ModelPage} from 'models/base';
import log from 'logger';


export default class DiscussionPage extends ModelPage {
    constructor(options) {
        super(options);
        this.$options.ns = 'discussions';
        this.$options.fetch = 'list_discussions';
    }
};
