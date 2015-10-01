import Dataset from 'models/dataset';
import log from 'logger';


export default class DatasetFull extends Dataset {
    /**
     * Fetch a full dataset (quality) given its identifier, either an ID or a slug.
     * @param  {String} ident The dataset identifier to fetch.
     * @return {Dataset}      The current object itself.
     */
    fetch(ident) {
        ident = ident || this.id || this.slug;
        if (ident) {
            this.$api('datasets.get_dataset_full', {dataset: ident}, this.on_fetched);
        } else {
            log.error('Unable to fetch full Dataset: no identifier specified');
        }
        return this;
    }
}
