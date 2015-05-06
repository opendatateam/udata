describe("Util plugin", function() {
    var Vue = require('vue');

    Vue.use(require('plugins/util'));

    describe('isFunction', function() {
        it('should be true if is a function', function() {
            expect(Vue.util.isFunction(function() {})).to.be.true();
        });

        it('should be false if is not a function', function() {
            expect(Vue.util.isFunction(42)).to.be.false();
        });
    });

    describe('serialize_form', function() {
        var form;

        beforeEach(function() {
            console.log('before', form, fixture.el);
            form = fixture.set('<form/>')[0][0];
            console.log('during', form, fixture.el);
        });

        afterEach(function() {
            fixture.cleanup();
            console.log('after', form, fixture.el);
        });

        it('should be an empty object for empty form', function() {
            expect(Vue.util.serialize_form(form)).to.eql({});
        });

        it('should not serialize empty inputs', function() {
            console.log('form', form);
            $(form)
                .append('<input name="input"/>')
                .append('<input type="checkbox" name="checkbox" value="cb1"/>')
                .append('<textarea name="textarea"></textarea>');

            expect(Vue.util.serialize_form(form)).to.eql({});
        });

        it('should serialize input values', function() {
            $(form)
                .append('<input name="input" value="a"/>')
                .append('<input type="checkbox" name="checkbox" value="cb1" checked=="checked"/>')
                .append('<textarea name="textarea">b</textarea>');

            expect(Vue.util.serialize_form(form)).to.eql({
                'input': 'a',
                'checkbox': 'cb1',
                'textarea': 'b'
            });
        });
    });

});
