import {Model} from 'models/base';
import log from 'logger';


export default class Resource extends Model {
    /**
     * Fetch a resource given its dataset identifier and own identifier.
     * @param  {String} datasetId  The dataset identifier of the resource to fetch.
     * @param  {String} resourceId The resource identifier to fetch.
     * @return {Resource}           The current object itself.
     */
    fetch(datasetId, resourceId) {
        if (datasetId && resourceId) {
            this.loading = true;
            this.$api('datasets.get_resource', {dataset: datasetId, rid: resourceId}, this.on_fetched);
        } else {
            log.error('Unable to fetch Resource: no identifier(s) specified');
        }
        return this;
    }
};
