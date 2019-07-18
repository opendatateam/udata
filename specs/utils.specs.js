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
            expect(u.isObject([42])).to.be.false;
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

    describe('parseQS', function() {
        it('should parse an empty string', function() {
            expect(u.parseQS('')).to.eql({});
            expect(u.parseQS('?')).to.eql({});
            expect(u.parseQS(null)).to.eql({});
            expect(u.parseQS(undefined)).to.eql({});
        });

        it('should parse a single key-value pair', function() {
            expect(u.parseQS('?key=value')).to.eql({key: 'value'});
            expect(u.parseQS('key=value')).to.eql({key: 'value'});
        });

        it('should parse multiple key-value pairs', function() {
            const qs = '?key1=value1&key2=value2&key3=value3';
            expect(u.parseQS(qs)).to.eql({
                key1: 'value1',
                key2: 'value2',
                key3: 'value3',
            });
        });

        it('should should decode value', function() {
            expect(u.parseQS('?key=value%20encoded')).to.eql({key: 'value encoded'});
        });

        it('should should decode key', function() {
            expect(u.parseQS('?key%2Fencoded=value')).to.eql({'key/encoded': 'value'});
        });
    });

    describe('escapeRegex', function() {
        it('should escape any special chars', function() {
            expect(u.escapeRegex('Chars: |\\{}()[]^$+*?.'))
                .to.eql('Chars: \\|\\\\\\{\\}\\(\\)\\[\\]\\^\\$\\+\\*\\?\\.');
        });

        it('should not touch other chars', function() {
            expect(u.escapeRegex('noop')).to.eql('noop');
        });
    });
});
