describe("Common Form features", function() {

    var Vue = require('vue');

    Vue.config.async = false;
    Vue.use(require('plugins/i18next'));
    Vue.use(require('plugins/util'));

    var BaseForm = require('components/form/base-form');

    afterEach(function() {
        fixture.cleanup();
    });

    describe("Empty form", function() {
        var vm = new Vue({
            el: fixture.set('<form/>')[0],
            mixins: [BaseForm]
        });

        it('should have sane defaults', function() {
            expect(vm).to.have.property('fill').to.be.false;
            expect(vm).to.have.property('readonly').to.be.false;
            expect(vm).to.have.property('fields').to.be.undefined;
            expect(vm).to.have.property('defs').to.be.undefined;
            expect(vm).to.have.property('model').to.be.undefined;
        });

        it('should have an empty schema', function() {
            expect(vm).to.have.property('schema');
            expect(vm.schema).to.eql({
                properties: {},
                required: []
            });
        });

        it('should validate', function() {
            expect(vm.validate()).to.be.true;
        });
    });

    describe("Forms with fields and defs", function() {
        var vm = new Vue({
            el: fixture.set('<form/>')[0],
            mixins: [BaseForm],
            data: {
                fields: [{
                    id: 'title',
                    label: 'Title'
                }, {
                    id: 'private',
                    label: 'Private'
                }],
                defs: {
                    properties: {
                        title: {
                            type: 'string'
                        },
                        private: {
                            type: 'boolean'
                        }
                    },
                    required: ['title']
                }
            }
        });

        it('should have a correct schema', function() {
            expect(vm).to.have.property('schema').to.eql({
                properties: {
                    title: {
                        type: 'string'
                    },
                    private: {
                        type: 'boolean'
                    }
                },
                required: ['title']
            });
        });
    });

});
