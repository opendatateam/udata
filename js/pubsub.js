/**
 * Pubsub for tracking events.
 *
 * Source: http://davidwalsh.name/pubsub-javascript
 */
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

    /**
     * Subscribe to a given topic
     * @param  {String}   topic    The topic identifier to subscribe to
     * @param  {Function} listener The callback executed on topic publication
     * @return {Object}            A subscription handle with a single remove method.
     */
    subscribe(topic, listener) {
        // // Create the topic's object if not yet created
        if (!this.has(topic)) {
            this.topics[topic] = [];
        }

        // Add the listener to queue
        const index = this.topics[topic].push(listener) - 1;

        // Provide handle back for removal of topic
        return {
            remove: () => {
                delete this.topics[topic][index];
            }
        };
    }

    /**
     * Unsubscribe to a given topic
     * @param  {String}   topic    The topic identifier to unsubscribe to
     * @param  {Function} listener The callback to unregister
     */
    unsubscribe(topic, listener) {
        if (!this.has(topic)) return;

        this.topics[topic].some((handler, index) => {
            if (handler === listener) {
                delete this.topics[topic][index];
                return true;
            }
        });
    }

    /**
     * Subscribe once to a given topic
     * @param  {String}   topic    The topic identifier to subscribe to
     * @param  {Function} listener The callback executed on topic publication
     */
    once(topic, listener) {
        const subscription = this.subscribe(topic, () => {
            subscription.remove();
            listener.apply(this, arguments);
        });
        return subscription;
    }

    /**
     * Publish some data on a topic
     * @param  {String}    topic The topic identifier
     * @param  {...[type]} args  A variable list of arguments to pass to the listeners
     */
    publish(topic, ...args) {
        // If the topic doesn't exist, or there's no listeners in queue, just leave
        if(!this.has(topic)) return;

        // Cycle through topics queue, fire!
        this.topics[topic].forEach(function(handler) {
            handler(...args);
        });
    }

    /**
     * Remove a topic (and all its listeners)
     * @param  {String} topic The topic identifier to remove
     */
    remove(topic) {
        if (this.has(topic)) {
            delete this.topics[topic];
        }
    }
}

export const pubsub = new PubSub();

export default pubsub;
