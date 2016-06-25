describe('Location Plugin', function() {
    const plugin = require('plugins/location');

    describe('installation', function() {
        const Vue = require('vue');

        beforeEach(function() {
            Vue.use(plugin);
        });

        it('expose a global Vue.location', function() {
            expect(Vue.location).to.be.defined;
            expect(Vue.location).to.be.instanceof(plugin.Location);
        });

        it('expose an instance $location', function() {
            expect(new Vue().$location).to.be.defined;
            expect(new Vue().$location).to.be.instanceof(plugin.Location);
        });
    });

    describe('attribute', function() {
        const Vue = require('vue');

        beforeEach(function() {
            Vue.use(plugin);
        });

        it('expose a parsed query string as query attribute', function() {
            expect(Vue.location.query).to.be.defined;
            expect(Vue.location.query).to.be.instanceof(Object);
        });
    });
});
