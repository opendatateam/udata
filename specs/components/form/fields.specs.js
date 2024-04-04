import API from 'api';
import Vue from 'vue';
import BaseForm from 'components/form/base-form';

describe('Common Fields features', function() {
    Vue.config.async = false;
    Vue.use(require('plugins/i18next'));
    Vue.use(require('plugins/util'));

    require('bootstrap');

    beforeEach(function() {
        this.vm = new Vue({
            el: fixture.set(`
                <form role="form" v-el:form>
                    <field v-for="field in fields" v-ref:fields :field="field"
                        :schema="schema" :model="model"></field>
                </form>`)[0],
            mixins: [BaseForm],
            components: {
                field: {
                    mixins: [require('components/form/base-field').BaseField]
                }
            }
        });
    });

    afterEach(function() {
        fixture.cleanup();
    });

    describe('Default field', function() {
        beforeEach(function() {
            this.vm.fields = [{
                id: 'test'
            }];
        });

        it('should have sane defaults', function() {
            const vm = this.vm.$refs.fields[0];
            expect(vm.field.id).to.equal('test');
            expect(vm.value).to.undefined;
            expect(vm.required).to.be.false;
            expect(vm.description).to.be.undefined;
            expect(vm.property).to.eql({});
            expect(vm.is_bool).to.be.false;
            expect(vm.placeholder).to.equal('');
            expect(vm.widget).to.equal('text-input');
        });

        it('should feed initial value from model', function() {
            this.vm.model = {test: 'test'};
            const vm = this.vm.$refs.fields[0];

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
            };
            const vm = this.vm.$refs.fields[0];

            expect(vm).to.have.deep.property('property.description', 'Test field');
            expect(vm).to.have.property('description', 'Test field');
            expect(vm.required).to.be.true;
        });
    });

    describe('Nested field', function() {
        beforeEach(function() {
            this.vm.fields = [{
                id: 'nested.test'
            }];
        });

        it('should have sane defaults', function() {
            const vm = this.vm.$refs.fields[0];
            expect(vm.field.id).to.equal('nested.test');
            expect(vm.value).to.be.undefined;
            expect(vm.required).to.be.false;
            expect(vm.description).to.be.undefined;
            expect(vm.property).to.eql({});
            expect(vm.is_bool).to.be.false;
            expect(vm.placeholder).to.equal('');
            expect(vm.widget).to.equal('text-input');
        });

        it('should feed value from model', function() {
            this.vm.model = {nested: {test: 'test'}};
            const vm = this.vm.$refs.fields[0];

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
            };
            const vm = this.vm.$refs.fields[0];

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

            const vm = this.vm.$refs.fields[0];
            expect(vm.field.id).to.equal('nested.test');
            expect(vm.value).to.undefined;
            expect(vm.required).to.be.true;
            expect(vm.description).to.be.undefined;
            expect(vm.property).to.eql({type: 'integer', format: 'int64'});
            expect(vm.is_bool).to.be.false;
            expect(vm.placeholder).to.equal('');
            expect(vm.widget).to.equal('number-input');
        });
    });
});
