import Raven from 'raven-js';
import config from 'config';

if (config.sentry) {
    const options = {
        logger: 'udata.js',  // Allow filtering in Sentry
        release: config.sentry.release,
        tags: config.sentry.tags,
    };

    Raven.config(config.sentry.dsn, options).install();
}

export default Raven;
