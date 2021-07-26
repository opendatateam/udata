import * as Sentry from '@sentry/vue';
import { Integrations } from '@sentry/tracing';
import config from './config';

function InitSentry(app) {
    if (config.sentry) {
        Sentry.init({
            app,
            dsn: config.sentry.dsn,
            integrations: [new Integrations.BrowserTracing()],
            release: config.sentry.release,
            ignoreErrors: [
                'AuthenticationRequired',  // Uncaught but managed
            ],
        })
        Sentry.setTags(config.sentry.tags)
    }
}

export default InitSentry;
