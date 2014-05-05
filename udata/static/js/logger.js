define([], function() {
    var DEBUG = false,
        Logger = {};
    //>>excludeStart('production', pragmas.production);
    DEBUG = true;
    //>>excludeEnd('production');

    if (!Function.prototype.bind) {
        Function.prototype.bind = function(oThis) {
            if (typeof this !== "function") {
                // closest thing possible to the ECMAScript 5 internal IsCallable function
                throw new TypeError("Function.prototype.bind - what is trying to be bound is not callable");
            }

            var aArgs = Array.prototype.slice.call(arguments, 1),
                fToBind = this,
                fNOP = function() {},
                fBound = function() {
                    return fToBind.apply(this instanceof fNOP && oThis ? this : oThis,
                        aArgs.concat(Array.prototype.slice.call(arguments)));
                };

            fNOP.prototype = this.prototype;
            fBound.prototype = new fNOP();

            return fBound;
        };
    }

    Logger.info = Function.prototype.bind.call(console.info, console);
    Logger.warn = Function.prototype.bind.call(console.warn, console);
    Logger.error = Function.prototype.bind.call(console.error, console);

    if (DEBUG) {
        Logger.log = Function.prototype.bind.call(console.log, console);
        Logger.debug = Function.prototype.bind.call(console.debug, console);
    } else {
        Logger.log = Logger.debug = function() {};
    }

    return Logger;
});
