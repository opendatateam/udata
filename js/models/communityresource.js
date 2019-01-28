import {Model} from 'models/base';
import log from 'logger';


export default class CommunityResource extends Model {
    /**
     * Fetch a community resource given its identifier, either an ID or a slug.
     * @param  {String} ident       The community resource identifier to fetch.
     * @return {CommunityResource}  The current object itself.
     */
    fetch(ident) {
        ident = ident || this.id;
        if (ident) {
            this.$api('datasets.retrieve_community_resource', {
                community: ident
            }, this.on_fetched);
        } else {
            log.error('Unable to fetch CommunityResource: no identifier specified');
        }
        return this;
    }

    /**
     * Create or update the given community resource
     */
    save(on_error) {
        if (this.id) {
            this.update(this, on_success, on_error);
        } else {
            this.$api('datasets.create_community_resource', {
                payload: this
            }, this.on_fetched, on_error);
        }
    }

    update(data, on_error) {
        this.$api('datasets.update_community_resource', {
            community: this.id,
            payload: data
        }, this.on_fetched, on_error);
    }
};
