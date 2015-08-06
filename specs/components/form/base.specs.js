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

        const PetSchema = {
            required: ['id', 'name'],
            properties: {
                id: {type: 'integer', format: 'int64'},
                name: {type: 'string'},
                tag: {type: 'string'}
            }
        };

        const PersonSchema = {
            required: ['id', 'name'],
            properties: {
                id: {type: 'integer', format: 'int64'},
                name: {type: 'string'},
                age: {type: 'integer'},
                pet: {$ref: '#/definitions/Pet'}
            }
        };

        class Pet extends Model {};
        class Person extends Model {};

        before(function() {
            API.mock_defs({
                Pet: PetSchema,
                Person: PersonSchema
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


});
