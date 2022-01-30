import {List} from 'models/base';
import log from 'logger';


export class ReuseTopics extends List {
    constructor(options) {
        super(options);
        this.$options.ns = 'reuses';
        this.$options.fetch = 'reuse_topics';
    }
};

export var reuse_topics = new ReuseTopics().fetch();
export default reuse_topics;
