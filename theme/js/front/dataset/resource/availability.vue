<template>
    <span v-if="checkAvailability" :class="['label', checkAvailability.class]">{{ checkAvailability.message }}</span>
</template>

<script>
export default {
    name: 'availability',
    props: {
        /**
         * Resource object as extracted from JSON-LD
         */
        resource: {
            type: Object,
        },
        /**
         * The url to get a refreshed check status from
         */
        checkurl: {
            type: String,
        },
        /**
         * A status to be used directly instead of parsing the resource and
         * calling checkurl
         */
        status: {
            type: Number,
        },
        /**
         * Does the resource need a refreshed check?
         */
        needCheck: {
            type: Boolean,
        },
    },
    data() {
        return {
            checkStatus: undefined,
        }
    },
    computed:{
        checkAvailability() {
            if (!this.checkStatus) return;
            if (this.checkStatus >= 200 && this.checkStatus < 400) {
                return {
                    message: this._('Available'),
                    class: 'label-success'
                }
            } else if (this.checkStatus >= 400 && this.checkStatus < 500) {
                return {
                    message: this._('Unavailable'),
                    class: 'label-danger'
                }
            } else if (this.checkStatus >= 500) {
                return {
                    message: this._('Unavailable (maybe temporary)'),
                    class: 'label-warning'
                }
            }
        },
    },
    created() {
        if (this.status) {
            this.checkStatus = this.status;
            return;
        }
        this.getResourceCheckStatus(this.resource, this.checkurl)
            .then((res) => {
                this.checkStatus = res['check:status'];
            })
            .catch(error => {
                console.log('Something went wrong with the linkchecker', error);
            });
    },
    methods: {
        /**
         * Get cached check or API check
         * @param  {Object} resource A resource element from DOM
         * @param  {String} checkurl The API check url
         */
        getResourceCheckStatus(resource, checkurl) {
            const cachedCheck = this.getCachedCheck(resource);
            return (cachedCheck && Promise.resolve(cachedCheck)) || this.$api.get(checkurl);
        },
        /**
         * Get a cached checked result from extras if resource is not flagged
         * as needing a new check
         * @param  {Object} resource A resource as extracted from JSON-LD
         */
        getCachedCheck(resource) {
            if (!this.needCheck) {
                const extras = this.getCheckExtras(resource.extras || []);
                if (extras['check:status']) {
                    return extras;
                }
            }
        },
        /**
         * Get check related extras from JSON-LD
         * @param {Array} extras A list of extras in JSON-LD format
         * @return {Object} Check extras as a hash, if any
         */
        getCheckExtras(extras) {
            return extras.reduce((obj, extra) => {
                if (extra.name.startsWith('check:')) {
                    obj[extra.name] = extra.value;
                }
                return obj;
            }, {});
        },
    },
}
</script>
