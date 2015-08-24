import {ModelPage} from 'models/base';
import log from 'logger';


export default class TopicPage extends ModelPage {
    constructor(options) {
        super(options);
        this.$options.ns = 'topics';
        this.$options.fetch = 'list_topics';
    }
};
