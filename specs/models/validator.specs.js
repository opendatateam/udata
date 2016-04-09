import config from 'config';
import Vue from 'vue';
import validator from 'models/validator';

describe('Model Schema and validation', function() {
    config.lang = 'en';
    Vue.use(require('plugins/i18next'));

    describe('Extra validation formats', function() {
        describe('date format', function() {
            const schema = {
                'type': 'string',
                'format': 'date'
            };

            it('should validate ISO 8601 date', function() {
                expect(validator.validate('2014-12-25', schema)).to.be.true;
            });

            it('should not validate wrong ISO 8601 date', function() {
                expect(validator.validate('2014-12-250', schema)).to.be.false;
                expect(validator.validate('unparsable', schema)).to.be.false;
                expect(validator.validate('2014-12', schema)).to.be.false;
            });

            it('should not validate ISO 8601 date-time', function() {
                expect(validator.validate('2014-12-25T09:30:26', schema)).to.be.false;
            });

            it('should handle leap years', function() {
                expect(validator.validate('2016-02-29', schema)).to.be.true;
                expect(validator.validate('2015-02-29', schema)).to.be.false;
            });
        });

        describe('date-time format', function() {
            const schema = {
                'type': 'string',
                'format': 'date-time'
            };

            it('should validate ISO 8601 date-time', function() {
                expect(validator.validate('2014-12-25T09:30:26', schema)).to.be.true;
                expect(validator.validate('2014-12-25T09:30', schema)).to.be.true;
            });

            it('should not validate wrong ISO 8601 date-time', function() {
                expect(validator.validate('unparsable', schema)).to.be.false;
            });

            it('should validate ISO 8601 date as date-time', function() {
                expect(validator.validate('2014-12-25', schema)).to.be.true;
            });

            it('should validate ISO 8601 date-time with milliseconds', function() {
                expect(validator.validate('2014-12-25T09:30:26.123', schema)).to.be.true;
            });

            it('should validate ISO 8601 date-time with UTF Offset', function() {
                expect(validator.validate('2014-12-25T09:30Z', schema)).to.be.true;
                expect(validator.validate('2014-12-25T09:30:26Z', schema)).to.be.true;
                expect(validator.validate('2014-12-25T09:30:26.123Z', schema)).to.be.true;

                expect(validator.validate('2014-12-25T09:30+02:00', schema)).to.be.true;
                expect(validator.validate('2014-12-25T09:30:26+02:00', schema)).to.be.true;
                expect(validator.validate('2014-12-25T09:30:26.123+02:00', schema)).to.be.true;
            });
        });
    });
});
