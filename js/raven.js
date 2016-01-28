import Raven from 'raven-js';
import config from 'config';

if (config.sentry) {
    const options = {
        logger: 'admin',
        release: config.sentry.release,
        tags: config.sentry.tags,
    }

    Raven.config(config.sentry.dsn, options).install()
}

export default Raven;
