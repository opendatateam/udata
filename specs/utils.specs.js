import u from 'utils';

describe('Utils', function() {
    describe('isFunction', function() {
        it('should be true if is a function', function() {
            expect(u.isFunction(function() {})).to.be.true;
        });

        it('should be false if is not a function', function() {
            expect(u.isFunction(42)).to.be.false;
        });
    });

    describe('isObject', function() {
        class Test {}

        it('should be true if is an Object', function() {
            expect(u.isObject({})).to.be.true;
            expect(u.isObject(new Test())).to.be.true;
        });

        it('should be false if is not an Object', function() {
            expect(u.isObject(42)).to.be.false;
            expect(u.isObject('42')).to.be.false;
            expect(u.isObject(true)).to.be.false;
            expect(u.isObject(null)).to.be.false;
            expect(u.isObject(undefined)).to.be.false;
        });
    });

    describe('isString', function() {
        it('should be true if is a String', function() {
            expect(u.isString('')).to.be.true;
            expect(u.isString('')).to.be.true;
        });

        it('should be false if is not a String', function() {
            expect(u.isString(null)).to.be.false;
            expect(u.isString(undefined)).to.be.false;
            expect(u.isString(45)).to.be.false;
            expect(u.isString(false)).to.be.false;
            expect(u.isString(true)).to.be.false;
            expect(u.isString({})).to.be.false;
            expect(u.isString([])).to.be.false;
        });
    });

    describe('getattr', function() {
        it('should fetch a root property', function() {
            const o = {attr: 'value'};
            expect(u.getattr(o, 'attr')).to.equal('value');
        });

        it('should fetch a nested property with dot-syntax', function() {
            const o = {nested: {attr: 'value'}};
            expect(u.getattr(o, 'nested.attr')).to.equal('value');
        });

        it('should return undefined if not found', function() {
            const o = {attr: 'value'};
            expect(u.getattr(o, 'other')).to.be.undefined;
        });
    });

    describe('setattr', function() {
        it('should set a root property', function() {
            const o = {};
            u.setattr(o, 'attr', 'value');
            expect(o).to.have.property('attr', 'value');
        });

        it('should set a nested property with dot-syntax', function() {
            const o = {nested: {}};
            u.setattr(o, 'nested.attr', 'value');
            expect(o.nested).to.have.property('attr', 'value');
        });

        it('should set intermediate properties if needed', function() {
            const o = {};
            u.setattr(o, 'nested.attr', 'value');
            expect(o).to.have.property('nested')
                .to.have.property('attr', 'value');
        });
    });
});
