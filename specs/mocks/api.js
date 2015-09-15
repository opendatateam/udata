define([
    'config',
    'vue',
    'specs/swagger/raw.json'
], function(config, Vue, raw_specs) {
    'use strict';

    // Mock the API and the Swagger specs
    config.api = 'http://localhost/api/1/swagger.json';

    var xhr = sinon.useFakeXMLHttpRequest(),
        requests = [];

    xhr.onCreate = function (req) { requests.push(req); };

    var API = require('api');

    requests[0].respond(200,
        {'Content-Type': 'application/json'},
        JSON.stringify(raw_specs)
    );

    xhr.restore();

    /**
     * An helper function to set API specifications
     * @param  {Object} specs A Full Swagger specifications
     */
    API.constructor.prototype.mock_specs = function(specs) {
        this.isBuilt = false;
        this.buildFromSpec(specs);
    };

    /**
     * An helper function to set API definitions
     * @param  {Object} defs A Swagger model definitions
     */
    API.constructor.prototype.mock_defs = function(defs) {
        var specs = $.extend(true, {},  raw_specs);

        specs.definitions = defs;
        this.mock_specs(specs);
    };

    return API;
});
