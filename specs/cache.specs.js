import {Cache, cache} from 'cache';

describe('Cache', function() {
    beforeEach(function() {
        sessionStorage.clear();
    });

    it('expose a global instance', function() {
        expect(cache).to.be.instanceof(Cache);
    });

    it('store and retrieve value', function() {
        const cache = new Cache('cache', sessionStorage);

        cache.set('key', 'value');
        expect(cache.get('key')).to.equal('value');
    });

    it('store and retrieve value with TTL', function() {
        const cache = new Cache('cache', sessionStorage);

        cache.set('key', 'value', 10);
        expect(cache.get('key')).to.equal('value');
    });

    it('expire value with default TTL', function(done) {
        const TTL = 1;
        const cache = new Cache('cache', sessionStorage, TTL);

        cache.set('key', 'value');

        setTimeout(() => {
            expect(cache.get('key')).to.be.undefined;
            done();
        }, 1000 * TTL + 1);
    });

    it('expire value with TTL', function(done) {
        const TTL = 1;
        const cache = new Cache('cache', sessionStorage);

        cache.set('key', 'value', TTL);

        setTimeout(() => {
            expect(cache.get('key')).to.be.undefined;
            done();
        }, 1000 * TTL + 1);
    });

    it('list all keys', function() {
        const cache = new Cache('cache', sessionStorage);
        const nbkeys = 3;

        sessionStorage.setItem('unrelated-key', 'value');

        [...Array(nbkeys).keys()].forEach(idx => {
            cache.set(`key-${idx}`, `value-${idx}`);
        });

        expect(cache.keys).to.have.length(nbkeys);
    });

    it('remove a value', function() {
        const cache = new Cache('cache', sessionStorage);

        cache.set('key', 'value');
        cache.remove('key');
        expect(cache.get('key')).to.be.undefined;
    });

    it('clear/remove all keys', function() {
        const cache = new Cache('cache', sessionStorage);
        const nbkeys = 3;

        sessionStorage.setItem('unrelated-key', 'value');

        [...Array(nbkeys).keys()].forEach(idx => {
            cache.set(`key-${idx}`, `value-${idx}`);
        });

        cache.clear();

        expect(sessionStorage).to.have.length(1);
    });
});
