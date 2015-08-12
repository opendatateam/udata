import API from 'specs/mocks/api';
import {Model} from 'models/base';
import Vue from 'vue';

describe("Common Form features", function() {

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

    describe('Form with model', function () {

        class Pet extends Model {};
        class Person extends Model {};

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
            var vm = new Vue({
                el: fixture.set('<form/>')[0],
                mixins: [BaseForm],
                data: {
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
            var vm = new Vue({
                el: fixture.set('<form/>')[0],
                mixins: [BaseForm],
                data: {
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

        var BaseField = require('components/form/base-field');

        beforeEach(function() {
            this.vm = new Vue({
                el: fixture.set(`
                    <form role="form" v-el="form">
                        <field v-repeat="field:fields" v-ref="fields"></field>
                    </form>`)[0],
                mixins: [BaseForm],
                components: {
                    field: {
                        template: `<component is="{{widget}}"></component>`,
                        mixins: [BaseField]
                    }
                },
                data: function() {
                    return {
                        fields: []
                    };
                }
            });
        });

        it('should be an empty object for empty form', function() {
            expect(this.vm.serialize()).to.eql({});
            expect(this.vm.serialize(true)).to.eql({});
        });

        it('should serialize all values', function() {
            this.vm.model = {};
            this.vm.defs = {properties: {
                checkbox: {
                    type: 'boolean'
                },
                textarea: {
                    type: 'string',
                    format: 'markdown'
                }
            }};
            this.vm.fields = [{
                    id: 'input'
                }, {
                    id: 'checkbox'
                }, {
                    id: 'textarea'
                }]

            expect(this.vm.serialize()).to.eql({
                input: '',
                checkbox: false,
                textarea: ''
            });
        });

        it('should serialize an empty object when no value changed', function() {
            this.vm.model = {};
            this.vm.defs = {properties: {
                checkbox: {
                    type: 'boolean'
                },
                textarea: {
                    type: 'string',
                    format: 'markdown'
                }
            }};
            this.vm.fields = [{
                    id: 'input'
                }, {
                    id: 'checkbox'
                }, {
                    id: 'textarea'
                }]

            expect(this.vm.serialize(true)).to.eql({});
        });


        it('should serialize changed input values', function() {
            this.vm.model = {};
            this.vm.defs = {properties: {
                checkbox: {
                    type: 'boolean'
                },
                textarea: {
                    type: 'string',
                    format: 'markdown'
                }
            }};
            this.vm.fields = [{
                id: 'input'
            }, {
                id: 'checkbox'
            }, {
                id: 'textarea'
            }, {
                id: 'untouched'
            }];

            this.vm.$$.form.querySelector('#input').value = 'a';
            this.vm.$$.form.querySelector('#checkbox').checked = true;
            this.vm.$$.form.querySelector('#textarea').value = 'b';

            expect(this.vm.serialize(true)).to.eql({
                'input': 'a',
                'checkbox': true,
                'textarea': 'b'
            });
        });

        it('should handle nested values', function() {
            this.vm.model = {};
            this.vm.fields = [{
                id: 'nested.a'
            }, {
                id: 'nested.b'
            }];

            this.vm.$$.form.querySelector('#nested\\.a').value = 'aa';
            this.vm.$$.form.querySelector('#nested\\.b').value = 'bb';

            expect(this.vm.serialize()).to.eql({
                nested: {
                    a: 'aa',
                    b: 'bb'
                }
            });
        });
    });

});
