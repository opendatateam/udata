var URL = require('url');
// ,
    // expect = chai.expect;

describe("API", function() {
    var config = require('config'),
        specs = require('specs/swagger/raw.json');

    beforeEach(function() {
        config.api = 'http://localhost/api/1/swagger.json';
        this.xhr = sinon.useFakeXMLHttpRequest();
        var requests = this.requests = [];
        this.xhr.onCreate = function (xhr) {
            requests.push(xhr);
        };
    });

    afterEach(function() {
        this.xhr.restore();
    });

    it("should fetch the swagger specs and trigger the built event", function() {
        var API = require('api'),
            callback = sinon.spy(),
            request;

        $(API).on('built', callback);

        request = this.requests[0];
        request.respond(200, {'Content-Type': 'application/json'}, JSON.stringify(specs));

        var url = URL.parse(request.url);
        url.search = null;

        expect(URL.format(url)).to.equal(config.api);
        expect(request.method).to.equal('GET');
        expect(callback).to.have.been.called();
        expect(API.isBuilt).to.equal(true);
        expect(API.url).to.equal(config.api);
        expect(API.info).to.eql(specs.info);
    });

});
