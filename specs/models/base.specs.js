describe('Base model', function() {
    var Vue = require('vue'),
        API = require('specs/mocks/api'),
        Model = require('models/base');

    Vue.config.async = false;

    var PetSchema = {
        required: ['id', 'name'],
        properties: {
            id: {type: 'integer', format: 'int64'},
            name: {type: 'string'},
            tag: {type: 'string'}
        }
    };

    describe('Flat model', function() {
        var Pet;

        before(function() {
            API.mock_defs({
                Pet: PetSchema
            });
            Pet = Model.extend({name: 'Pet'});
        });


        it("should use the specs schema", function() {
            var pet = new Pet();

            expect(pet.schema).not.to.be.undefined;
            expect(pet.schema).to.deep.equals(PetSchema);
        });

        it("should populate required data with the schema", function() {
            var pet = new Pet();

            expect(pet.$data).not.to.be.undefined;
            expect(pet.id).to.be.null;
            expect(pet.name).to.be.null;
            expect(pet.tag).to.be.undefined;
        });

        it('can be populated with the data', function() {
            var pet = new Pet({
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

        it('allow to watch undefined properties', function(done) {
            var pet = new Pet({
                    watch: {
                        'tag': function(value, old) {
                            done();
                        }
                    }
                });


            expect(pet.id).to.be.null;
            expect(pet.name).to.be.null;
            expect(pet.tag).to.be.undefined;

            pet.tag = 'test';
        });

        describe('Validation', function() {
            it("should validate complete valid models", function() {
                var pet = new Pet({
                        data: {
                            id: 1,
                            name: 'Rex',
                            tag: ''
                        }
                    });

                var result = pet.validate();

                expect(result.valid).to.be.true;
                expect(result.errors.length).to.equal(0);
                expect(result.missing.length).to.equal(0);
            });

            it("should validate complete valid nested models", function() {
                var pet = new Pet({
                        data: {
                            id: 1,
                            name: 'Rex',
                            tag: ''
                        }
                    });

                var result = pet.validate();

                expect(result.valid).to.be.true;
                expect(result.errors.length).to.equal(0);
                expect(result.missing.length).to.equal(0);
            });

            xit("should validate partial valid models", function() {
                // Need https://github.com/geraintluff/tv4/pull/175
                var pet = new Pet({
                        data: {
                            id: 1,
                            name: 'Rex'
                        }
                    });

                var result = pet.validate();

                expect(result.valid).to.be.true;
                expect(result.errors.length).to.equal(0);
                expect(result.missing.length).to.equal(0);
            });
        });
    });


    describe("Nested models", function() {

        var Person;

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
            Person = Model.extend({name: 'Person'});
        });

        it("should populate required data with the schema", function() {
            var person = new Person();

            expect(person.$data).not.to.be.undefined;
            expect(person.id).to.be.null;
            expect(person.name).to.be.null;
            expect(person.age).to.be.undefined;
            expect(person.pet).to.be.undefined;
        });

        it('can be populated with the data', function() {
            var person = new Person({
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

        it('allow to watch undefined properties', function(done) {
            var person = new Person({
                    watch: {
                        'pet.name': function(value, old) {
                            expect(value).to.equal('Rex');
                            done();
                        }
                    }
                });


            expect(person.pet).to.be.undefined;

            person.pet = {id: 1, name: 'Rex'};
            expect(person.pet.name).to.equal('Rex');
        });
    });

});
