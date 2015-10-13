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
    save() {
        if (this.id) {
            this.update(this);
        } else {
            this.$api('datasets.create_community_resource', {
                payload: this
            },
            this.on_fetched);
        }
    }

    update(data) {
        this.$api('datasets.update_community_resource', {
            community: this.id,
            payload: data
        }, () => {
            this.fetch(this.id);
        });
    }
};
