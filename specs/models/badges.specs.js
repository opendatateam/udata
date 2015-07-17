import API from 'specs/mocks/api';
import {Badges, BadgeError} from 'models/badges';

describe('Badges cache', function() {

    var BadgeableSchema = {
            required: ['id', 'name'],
            properties: {
                id: {type: 'integer', format: 'int64'},
                name: {type: 'string'},
                tag: {type: 'string'},
                badges: {}
            }
        },
        NonBadgeableSchema = {
            required: ['id', 'name'],
            properties: {
                id: {type: 'integer', format: 'int64'},
                name: {type: 'string'},
                tag: {type: 'string'}
            }
        },
        badges;

    before(function() {
        API.mock_specs({
            definitions: {
                Badgeable: BadgeableSchema,
                NonBadgeable: NonBadgeableSchema
            },
            paths: {
                '/badgeable': {
                    get: {
                        operationId: 'available_badgeable_badges',
                        tags: ['badgeables']
                    }
                }
            }
        });
    });

    beforeEach(function() {
        badges = new Badges();
        this.xhr = sinon.useFakeXMLHttpRequest();
        let requests = this.requests = [];
        this.xhr.onCreate = function (req) { requests.push(req); };
    });

    afterEach(function() {
        this.xhr.restore();
    });

    it('should allow access to existing badgeable models', function() {
        expect(badges.badgeable).not.to.be.undefined;
    });

    it('should raise a BadgeError when trying to access a non badgeable model', function() {
        expect(badges.nonbadgeable).to.be.undefined;
    });

    it('should raise a BadgeError when trying to access a non-existant model', function() {
        expect(badges.notfound).to.be.undefined;
    });

    it('should fetch values on first access', function() {
        let result = badges.badgeable,
            response = JSON.stringify({
                badge1: 'Badge 1',
                badge2: 'Badge 2'
            });

        expect(this.requests).to.have.length(1);

        this.requests[0].respond(200, {'Content-Type': 'application/json'}, response);

        expect(result.badge1).to.equal('Badge 1');
    });

    it('should use cache on next accesses', function() {
        expect(this.requests).to.have.length(0);

        let result = badges.badgeable,
            response = JSON.stringify({
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

});
