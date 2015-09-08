import API from 'specs/mocks/api';
import { Model } from 'models/base';
import Vue from 'vue';

describe("Common Fields features", function() {

    Vue.config.async = false;
    Vue.use(require('plugins/i18next'));
    Vue.use(require('plugins/util'));

    require('bootstrap');

    before(function () {
        // Need to mock reference lists
        // API.mock_specs(require('specs/mocks/udata-swagger.json'));
    });

    beforeEach(function() {
        this.vm = new Vue({
            el: fixture.set(`
                <form role="form" v-el="form">
                    <field v-repeat="field:fields" v-ref="field"></field>
                </form>`),
            mixins: [require('components/form/base-form')],
            components: {
                field: {
                    mixins: [require('components/form/base-field')]
                }
            }
        });
    });

    afterEach(function() {
        fixture.cleanup();
    });

    describe("Default field", function() {

        beforeEach(function() {
            this.vm.fields = [{
                id: 'test'
            }];
        });

        it('should have sane defaults', function() {
            let vm = this.vm.$.field[0];
            expect(vm.field.id).to.equal('test');
            expect(vm.value).to.equal('');
            expect(vm.required).to.be.false;
            expect(vm.description).to.be.undefined;
            expect(vm.property).to.eql({});
            expect(vm.is_bool).to.be.false;
            expect(vm.placeholder).to.equal('');
            expect(vm.widget).to.equal('text-input');
        });

        it('should feed value from model', function() {
            this.vm.model = {test: 'test'};
            let vm = this.vm.$.field[0];

            expect(vm.value).to.equal('test');
        });

        it('should use provided schema data', function() {
            this.vm.defs = {
                properties: {
                    test: {
                        description: 'Test field'
                    }
                },
                required: ['test']
            }
            let vm = this.vm.$.field[0];

            expect(vm).to.have.deep.property('property.description', 'Test field');
            expect(vm).to.have.property('description', 'Test field');
            expect(vm.required).to.be.true;
        });

    });

    describe("Nested field", function() {

        beforeEach(function() {
            this.vm.fields = [{
                id: 'nested.test'
            }];
        });

        it('should have sane defaults', function() {
            let vm = this.vm.$.field[0];
            expect(vm.field.id).to.equal('nested.test');
            expect(vm.value).to.equal('');
            expect(vm.required).to.be.false;
            expect(vm.description).to.be.undefined;
            expect(vm.property).to.eql({});
            expect(vm.is_bool).to.be.false;
            expect(vm.placeholder).to.equal('');
            expect(vm.widget).to.equal('text-input');
        });

        it('should feed value from model', function() {
            this.vm.model = {nested: {test: 'test'}};
            let vm = this.vm.$.field[0];

            expect(vm.value).to.equal('test');
        });

        it('should use provided schema data', function() {
            this.vm.defs = {
                properties: {
                    'nested.test': {
                        description: 'Test field'
                    }
                },
                required: ['nested.test']
            }
            let vm = this.vm.$.field[0];

            expect(vm).to.have.deep.property('property.description', 'Test field');
            expect(vm).to.have.property('description', 'Test field');
            expect(vm.required).to.be.true;
        });

        it('should resolve $refs', function() {
            API.mock_defs({
                Nested: {
                    required: ['test'],
                    properties: {
                        test: {type: 'integer', format: 'int64'},
                        name: {type: 'string'},
                        tag: {type: 'string'}
                    }
                },
                Root: {
                    required: ['nested'],
                    properties: {
                        id: {type: 'integer', format: 'int64'},
                        name: {type: 'string'},
                        age: {type: 'integer'},
                        nested: {$ref: '#/definitions/Nested'}
                    }
                }
            });

            this.vm.defs = {$ref: '#/definitions/Root'};

            let vm = this.vm.$.field[0];
            expect(vm.field.id).to.equal('nested.test');
            expect(vm.value).to.equal('');
            expect(vm.required).to.be.true;
            expect(vm.description).to.be.undefined;
            expect(vm.property).to.eql({type: 'integer', format: 'int64'});
            expect(vm.is_bool).to.be.false;
            expect(vm.placeholder).to.equal('');
            expect(vm.widget).to.equal('text-input');
        });

    });

});
