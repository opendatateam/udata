import API from 'api';
import {Model} from 'models/base';
import Vue from 'vue';

Vue.config.async = false;

describe('Base model', function() {
    const PetSchema = {
        required: ['id', 'name'],
        properties: {
            id: {type: 'integer', format: 'int64'},
            name: {type: 'string'},
            tag: {type: 'string'}
        }
    };

    describe('Flat model', function() {
        class Pet extends Model {}

        before(function() {
            API.mock_defs({
                Pet: PetSchema
            });
        });


        it('should use the specs schema', function() {
            const pet = new Pet();

            expect(pet.__schema__).not.to.be.undefined;
            expect(pet.__schema__).to.deep.equals(PetSchema);
        });

        it('should populate required data with the schema', function() {
            const pet = new Pet();

            expect(pet.id).to.be.null;
            expect(pet.name).to.be.null;
            expect(pet.tag).to.be.undefined;
        });

        it('can be populated with the data', function() {
            const pet = new Pet({
                data: {
                    id: 1,
                    name: 'Rex',
                    tag: 'tag'
                }
            });

            expect(pet.id).to.equal(1);
            expect(pet.name).to.equal('Rex');
            expect(pet.tag).to.equal('tag');
        });

        describe('Vue.js integration', function() {
            it('allows to watch undefined properties', function(done) {
                const vm = new Vue({
                    data: {
                        pet: new Pet()
                    },
                    watch: {
                        'pet.tag': function() {
                            done();
                        }
                    }
                });

                expect(vm.pet.id).to.be.null;
                expect(vm.pet.name).to.be.null;
                expect(vm.pet.tag).to.be.undefined;

                vm.pet.tag = 'test';
            });
        });


        describe('Validation', function() {
            it('should validate complete valid models', function() {
                const pet = new Pet({
                    data: {
                        id: 1,
                        name: 'Rex',
                        tag: ''
                    }
                });

                const result = pet.validate();

                expect(result.valid).to.be.true;
                expect(result.errors.length).to.equal(0);
                expect(result.missing.length).to.equal(0);
            });

            it('should validate complete valid nested models', function() {
                const pet = new Pet({
                    data: {
                        id: 1,
                        name: 'Rex',
                        tag: ''
                    }
                });

                const result = pet.validate();

                expect(result.valid).to.be.true;
                expect(result.errors.length).to.equal(0);
                expect(result.missing.length).to.equal(0);
            });

            xit('should validate partial valid models', function() {
                // Need https://github.com/geraintluff/tv4/pull/175
                const pet = new Pet({
                    data: {
                        id: 1,
                        name: 'Rex'
                    }
                });

                const result = pet.validate();

                expect(result.valid).to.be.true;
                expect(result.errors.length).to.equal(0);
                expect(result.missing.length).to.equal(0);
            });
        });
    });


    describe('Nested models', function() {
        class Person extends Model {}

        before(function() {
            API.mock_defs({
                Pet: PetSchema,
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

        it('should populate required data with the schema', function() {
            const person = new Person();

            expect(person.id).to.be.null;
            expect(person.name).to.be.null;
            expect(person.age).to.be.undefined;
            expect(person.pet).to.be.undefined;
        });

        it('can be populated with the data', function() {
            const person = new Person({
                data: {
                    id: 1,
                    name: 'Axel',
                    age: 30,
                    pet: {
                        id: 1,
                        name: 'Rex'
                    }
                }
            });

            expect(person.id).to.equal(1);
            expect(person.name).to.equal('Axel');
            expect(person.age).to.equal(30);
            expect(person.pet).not.to.be.undefined;
            expect(person.pet.id).to.equal(1);
            expect(person.pet.name).to.equal('Rex');
        });

        describe('Vue.js integration', function() {
            it('allows to watch undefined properties', function(done) {
                const vm = new Vue({
                    data: {
                        person: new Person()
                    },
                    watch: {
                        'person.pet.name': function(value) {
                            expect(value).to.equal('Rex');
                            done();
                        }
                    }
                });

                expect(vm.person.pet).to.be.undefined;

                vm.person.pet = {id: 1, name: 'Rex'};
                expect(vm.person.pet.name).to.equal('Rex');
            });
        });
    });
});
