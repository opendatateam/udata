/**
 * Base inheritable class for custom error.
 *
 * Ensure stack trace preservation and proper Sentry type
 */
export default class CustomError extends Error {
    constructor(...args) {
        super(...args);
        this.name = this.constructor.name;
        Error.captureStackTrace(this, this.constructor);
    }
}
