import * as Sentry from '@sentry/vue';
import { Integrations } from '@sentry/tracing';
import Vue from 'vue';
import config from 'config';

if (config.sentry) {
    Sentry.init({
        Vue: Vue,
        dsn: config.sentry.dsn,
        integrations: [new Integrations.BrowserTracing()],
        release: config.sentry.release,
        ignoreErrors: [
            'AuthenticationRequired',  // Uncaught but managed
        ],
    })

    Sentry.setTags(config.sentry.tags)
}

export default Sentry;
