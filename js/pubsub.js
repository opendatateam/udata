/**
 * Pubsub for tracking events.
 *
 * Source: http://davidwalsh.name/pubsub-javascript
 */

// var topics = {};
// var hOP = topics.hasOwnProperty;

export class PubSub {
    constructor() {
        this.topics = {};
    }

    /**
     * Check if topic exists
     * @param  {String}  topic The topic name
     * @return {Boolean}       True if the topic exists
     */
    has(topic) {
        return this.topics.hasOwnProperty(topic);
    }

    subscribe(topic, listener) {
        // // Create the topic's object if not yet created
        if (!this.has(topic)) {
            this.topics[topic] = [];
        }
        // if(!hOP.call(topics, topic)) topics[topic] = [];

        // Add the listener to queue
        var index = this.topics[topic].push(listener) -1;

        // Provide handle back for removal of topic
        return {
            remove: function() {
                delete this.topics[topic][index];
            }
        };
    }

    unsubscribe(topic, listener) {
        if (!this.has(topic)) return;

        this.topics[topic].some(function(handler, index) {
            if (handler === listener) {
                delete this.topics[topic][index];
                return true;
            }
        });
    }

    publish(topic, ...args) {
        // If the topic doesn't exist, or there's no listeners in queue, just leave
        if(!this.has(topic)) return;

        // Cycle through topics queue, fire!
        this.topics[topic].forEach(function(handler) {
            handler(...args);
        });
    }

    remove(topic) {
        if (this.has(topic)) {
            delete this.topics[topic];
        }
    }
};

export var pubsub = new PubSub();

export default pubsub;
