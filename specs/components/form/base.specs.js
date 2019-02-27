import API from 'api';
import {Model} from 'models/base';
import Vue from 'vue';
import BaseForm from 'components/form/base-form';

describe('Common Form features', function() {
    Vue.config.async = false;

    Vue.use(require('plugins/i18next'));
    Vue.use(require('plugins/util'));


    afterEach(function() {
        fixture.cleanup();
    });

    describe('Empty form', function() {
        beforeEach(function() {
            this.vm = new Vue({
                el: fixture.set('<form v-el:form />')[0],
                mixins: [BaseForm]
            });
        });

        it('should have sane defaults', function() {
            expect(this.vm).to.have.property('fill').to.be.false;
            expect(this.vm).to.have.property('readonly').to.be.false;
            expect(this.vm).to.have.property('fields').to.be.undefined;
            expect(this.vm).to.have.property('defs').to.be.undefined;
            expect(this.vm).to.have.property('model').to.be.undefined;
        });

        it('should have an empty schema', function() {
            expect(this.vm).to.have.property('schema');
            expect(this.vm.schema).to.eql({
                properties: {},
                required: []
            });
        });

        it('should validate', function() {
            expect(this.vm.validate()).to.be.true;
        });
    });

    describe('Forms with fields and defs', function() {
        it('should have a correct schema', function() {
            const vm = new Vue({
                el: fixture.set('<form v-el:form/>')[0],
                mixins: [BaseForm],
                propsData: {
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

    describe('Form with model', function() {
        class Pet extends Model {}
        class Person extends Model {}

        before(function() {
            API.mock_defs({
                Pet: {
                    required: ['id', 'name'],
                    properties: {
                        id: {type: 'integer', format: 'int64'},
                        name: {type: 'string'},
                        tag: {type: 'string'}
                    }
                },
                Person: {
                    required: ['id', 'name'],
                    properties: {
                        id: {type: 'integer', format: 'int64'},
                        name: {type: 'string'},
                        age: {type: 'integer'},
                        pet: {$ref: '#/definitions/Pet'}
                    }
                }
            });
        });

        it('Should handle schema for flat models', function() {
            const vm = new Vue({
                el: fixture.set('<form/>')[0],
                mixins: [BaseForm],
                propsData: {
                    model: new Pet(),
                    fields: [{
                        id: 'id'
                    }, {
                        id: 'name'
                    }]
                }
            });

            expect(vm).to.have.property('schema').to.eql({
                required: ['id', 'name'],
                properties: {
                    id: {type: 'integer', format: 'int64'},
                    name: {type: 'string'}
                }
            });
        });

        it('Should handle schema for nested models', function() {
            const vm = new Vue({
                el: fixture.set('<form/>')[0],
                mixins: [BaseForm],
                propsData: {
                    model: new Person(),
                    fields: [{
                        id: 'id'
                    }, {
                        id: 'pet.name'
                    }]
                }
            });

            expect(vm).to.have.property('schema').to.eql({
                required: ['id'],
                properties: {
                    id: {type: 'integer', format: 'int64'},
                    'pet.name': {type: 'string'}
                }
            });
        });
    });


    describe('serialization', function() {
        beforeEach(function() {
            API.mock_defs({});
            this.vm = new Vue({
                el: fixture.set(`
                    <form role="form" v-el:form>
                        <field v-for="field in fields" v-ref:fields :field="field"
                            :schema="schema" :model="model">
                        </field>
                    </form>
                `)[0],
                mixins: [BaseForm],
                components: {
                    field: {
                        template: `<component :is="widget"
                                    :field="field" :value="value" :model="model"
                                    :description="description" :property="property"
                                    :placeholder="placeholder" :required="required"
                                    :readonly="readonly">
                                </component>`,
                        mixins: [require('components/form/base-field').BaseField]
                    }
                }
            });
        });

        it('should be an empty object for empty form', function() {
            expect(this.vm.serialize()).to.eql({});
        });

        it('should serialize all values', function() {
            this.vm.defs = {properties: {
                // Input is optional, just to avoid console warnings
                input: {type: 'string'},
                checkbox: {type: 'boolean'},
                textarea: {type: 'string', format: 'markdown'},
                select: {type: 'string', enum: ['a', 'b'], default: 'b'},
            }};
            this.vm.fields = [
                {id: 'input'},
                {id: 'checkbox'},
                {id: 'textarea'},
                {id: 'select'}
            ];

            expect(this.vm.serialize()).to.eql({
                input: undefined,
                checkbox: false,
                textarea: undefined,
                select: 'b',
            });
        });

        it('should serialize updated values', function() {
            this.vm.defs = {properties: {
                // Input is optional, just to avoid console warnings
                input: {type: 'string'},
                checkbox: {type: 'boolean'},
                textarea: {type: 'string', format: 'markdown'},
                select: {type: 'string', enum: ['a', 'b']},
            }};
            this.vm.fields = [
                {id: 'input'},
                {id: 'checkbox'},
                {id: 'textarea'},
                {id: 'select'},
            ];

            this.vm.$el.querySelector('#input').value = 'a';
            this.vm.$el.querySelector('#checkbox').checked = true;
            this.vm.$el.querySelector('#textarea').value = 'aa';
            this.vm.$el.querySelector('#select').value = 'b';

            expect(this.vm.serialize()).to.eql({
                input: 'a',
                checkbox: true,
                textarea: 'aa',
                select: 'b',
            });
        });

        describe('Nested values', function() {
            it('should handle nested values', function() {
                // Defs are optional, just here to avoid console warnings
                this.vm.defs = {properties: {
                    'nested.a': {type: 'string'},
                    'nested.b': {type: 'string'},
                }};
                this.vm.fields = [
                    {id: 'nested.a'},
                    {id: 'nested.b'},
                ];

                this.vm.$els.form.querySelector('#nested\\.a').value = 'aa';
                this.vm.$els.form.querySelector('#nested\\.b').value = 'bb';

                expect(this.vm.serialize()).to.eql({
                    nested: {
                        a: 'aa',
                        b: 'bb'
                    }
                });
            });

            it('should not serialize empty nested nested object', function() {
                // Defs are optional, just here to avoid console warnings
                this.vm.defs = {properties: {
                    'nested.a': {type: 'string'},
                    'nested.b': {type: 'string'},
                }};
                this.vm.fields = [
                    {id: 'nested.a'},
                    {id: 'nested.b'},
                ];

                expect(this.vm.serialize()).to.eql({});
            });

            it('should serialize empty nested object if required', function() {
                API.mock_defs({
                    Nested: {properties: {
                        a: {type: 'string'},
                        b: {type: 'string'}
                    }}
                });
                this.vm.defs = {
                    properties: {
                        'nested': {$ref: '#/definitions/Nested'}
                    },
                    required: ['nested']
                };
                this.vm.fields = [
                    {id: 'nested.a'},
                    {id: 'nested.b'},
                ];

                expect(this.vm.serialize()).to.eql({
                    nested: {
                        a: undefined,
                        b: undefined
                    }
                });
            });
        });
    });
});
