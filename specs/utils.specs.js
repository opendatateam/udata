import u from 'utils';

describe("Utils", function() {

    describe('isFunction', function() {
        it('should be true if is a function', function() {
            expect(u.isFunction(function() {})).to.be.true;
        });

        it('should be false if is not a function', function() {
            expect(u.isFunction(42)).to.be.false;
        });
    });

    describe('getattr', function() {
        it('should fetch a root property', function() {
            let o = {attr: 'value'};
            expect(u.getattr(o, 'attr')).to.equal('value');
        });

        it('should fetch a nested property with dot-syntax', function() {
            let o = {nested: {attr: 'value'}};
            expect(u.getattr(o, 'nested.attr')).to.equal('value');
        });

        it('should return undefined if not found', function() {
            let o = {attr: 'value'};
            expect(u.getattr(o, 'other')).to.be.undefined;
        });
    });


});
