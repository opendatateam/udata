describe("Util plugin", function() {
    var Vue = require('vue');

    Vue.use(require('plugins/util'));

    describe('isFunction', function() {
        it('should be true if is a function', function() {
            expect(Vue.util.isFunction(function() {})).to.be.true;
        });

        it('should be false if is not a function', function() {
            expect(Vue.util.isFunction(42)).to.be.false;
        });
    });

});
