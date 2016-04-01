import API from 'api';
import {Badges, BadgeError} from 'models/badges';

describe('Badges', function() {
    let badges;
    const TYPES = {
        badgeable: 'badgeables',
        notfound: 'not_found'
    };

    class Badgeable {
        constructor() {
            this.id = 'identifier';
            this.badges = [];
        }
    }
    Badgeable.__badges_type__ = 'badgeable';

    before(function() {
        // Mock a full badge schema for badgeable
        API.mock_specs({
            definitions: {
                Badge: {
                    required: ['kind'],
                    properties: {kind: {type: 'string'}}
                }
            },
            paths: {
                '/': {
                    get: {
                        operationId: 'available_badgeable_badges',
                        tags: ['badgeables']
                    }
                },
                '/{badgeable}/': {
                    post: {
                        operationId: 'add_badgeable_badge',
                        parameters: [{
                            in: 'body',
                            name: 'payload',
                            required: true,
                            schema: {$ref: '#/definitions/Badge'}
                        }, {
                            in: 'path',
                            name: 'badgeable',
                            required: true,
                            type: 'string'
                        }],
                        tags: ['badgeables']
                    }
                },
                '/{badgeable}/{badge_kind}/': {
                    delete: {
                        operationId: 'delete_badgeable_badge',
                        parameters: [{
                            in: 'path',
                            name: 'badge_kind',
                            required: true,
                            type: 'string'
                        }, {
                            in: 'path',
                            name: 'badgeable',
                            required: true,
                            type: 'string'
                        }],
                        tags: ['badgeables']
                    }
                }
                        // ,
                        // "responses": {"200": {"description": "Success"}}, "tags": ["datasets"]}},
            }
        });
    });

    beforeEach(function() {
        badges = new Badges(TYPES);
        this.xhr = sinon.useFakeXMLHttpRequest();
        const requests = this.requests = [];
        this.xhr.onCreate = function(req) { requests.push(req); };
    });

    afterEach(function() {
        this.xhr.restore();
    });

    it('should allow access to existing badgeable models', function() {
        expect(badges.badgeable).not.to.be.undefined;
    });

    it('should not have attribute for a non badgeable model', function() {
        expect(badges.nonbadgeable).to.be.undefined;
    });

    it.skip('should raise a BadgeError when trying to access a non-existant model', function() {
        function test() {badges.notfound;}
        expect(test).to.throw(BadgeError);
    });

    it('should fetch values on first access', function() {
        const result = badges.badgeable; // Trigger fetch
        const response = JSON.stringify({
            badge1: 'Badge 1',
            badge2: 'Badge 2'
        });

        expect(this.requests).to.have.length(1);

        this.requests[0].respond(200, {'Content-Type': 'application/json'}, response);

        expect(result.badge1).to.equal('Badge 1');
    });

    it('should use cache on next accesses', function() {
        expect(this.requests).to.have.length(0);

        const result = badges.badgeable; // Trigger fetch
        const response = JSON.stringify({
            badge1: 'Badge 1',
            badge2: 'Badge 2'
        });

        expect(this.requests).to.have.length(1);

        this.requests[0].respond(200, {'Content-Type': 'application/json'}, response);

        expect(badges.badgeable.badge1).to.equal('Badge 1');
        expect(this.requests).to.have.length(1);

        expect(badges.badgeable.badge2).to.equal('Badge 2');
        expect(this.requests).to.have.length(1);
    });

    it('should list available badges for a given object', function() {
        const obj = new Badgeable();

        const result = badges.badgeable; // Trigger fetch
        const response = JSON.stringify({
            badge1: 'Badge 1',
            badge2: 'Badge 2'
        });

        this.requests[0].respond(200, {'Content-Type': 'application/json'}, response);

        expect(badges.available(obj)).to.equal(badges.badgeable);
    });

    it('should add a badge for a given object', function(done) {
        const obj = new Badgeable();

        badges.add(obj, 'badge-1', function(badge) {
            expect(obj.badges).to.have.length(1).to.contain(badge);
            expect(badge.kind).to.equal('badge-1');
            done();
        });

        expect(this.requests).to.have.length(1);

        const payload = JSON.stringify({kind: 'badge-1'});
        const request = this.requests[0];

        expect(request.url).to.equal('http://localhost/identifier/?lang=en');
        expect(request.method).to.equal('POST');
        expect(request.requestBody).to.equal(payload);

        request.respond(200, {'Content-Type': 'application/json'}, payload);
    });

    it('should delete a badge for a given object', function(done) {
        const obj = new Badgeable();
        obj.badges.push({kind: 'badge-1'});

        badges.remove(obj, 'badge-1', function() {
            expect(obj.badges).to.be.empty;
            done();
        });

        expect(this.requests).to.have.length(1);

        const request = this.requests[0];

        expect(request.url).to.equal('http://localhost/identifier/badge-1/?lang=en');
        expect(request.method).to.equal('DELETE');

        request.respond(204, {'Content-Type': 'application/json'}, '');
    });
});
