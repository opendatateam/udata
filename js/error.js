/**
 * Base inheritable class for custom error.
 *
 * Ensure stack trace preservation and proper Sentry type
 */
export default class CustomError extends Error {
    constructor(...args) {
        super(...args);
        this.name = this.constructor.name;
        if (typeof Error.captureStackTrace === 'function') {
            // Stack trace in V8
            Error.captureStackTrace(this, this.constructor);
        } else {
            // Firefox and other browser not supporting Error.captureStackTrace
            this.stack = (new Error()).stack;
        }
    }
}
