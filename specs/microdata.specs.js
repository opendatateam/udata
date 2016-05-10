import microdata from 'microdata';

describe('microdata', function() {
    before(function() {
        fixture.setBase('specs/fixtures/microdata');
    });

    afterEach(function() {
        fixture.cleanup();
    });

    it('should find Mark Pilgrim', function() {
        fixture.load('person.html');
        const el = fixture.load('person.html')[0];
        expect(microdata('http://data-vocabulary.org/Person')).to.deep.equal([{
            $type: 'http://data-vocabulary.org/Person',
            $el: el,
            photo: 'http://diveintohtml5.info/examples/2000_05_mark.jpg',
            name: 'Mark Pilgrim',
            title: 'Developer advocate',
            affiliation: ['Google, Inc.', 'O\'Reilly'],
            address: [{
                $type: 'http://data-vocabulary.org/Address',
                $el: document.getElementById('address-1'),
                'street-address': 'P.O. Box 562',
                locality: 'Anytown',
                region: 'PA',
                'postal-code': '12345',
                'country-name': 'USA',
            }, {
                $type: 'http://data-vocabulary.org/Address',
                $el: document.getElementById('address-2'),
                'street-address': '100 Main Street',
                locality: 'Anytown',
                region: 'PA',
                'postal-code': '19999',
                'country-name': 'USA',
            }],
            url: [
                'http://www.google.com/profiles/pilgrim',
                'http://www.reddit.com/user/MarkPilgrim',
                'http://www.twitter.com/diveintomark'
            ]
        }]);
    });

    it('should extract itemid if present', function() {
        const el = fixture.load('with-id.html')[0];
        expect(microdata('http://udata.org/Test')).to.deep.equal([{
            $type: 'http://udata.org/Test',
            $el: el,
            id: 'my-identifier'
        }]);
    });

    it('should works with deep nesting', function() {
        const el = fixture.load('nested.html')[0];
        expect(microdata('http://udata.org/Test')).to.deep.equal([{
            $type: 'http://udata.org/Test',
            $el: el,
            id: 'my-identifier',
            nested: {
                $type: 'http://udata.org/Nested',
                $el: document.getElementById('nested'),
                id: 'my-nested-identifier',
                'nested-value': 'value',
            }
        }]);
    });
});
