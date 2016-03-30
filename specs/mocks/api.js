import config from 'config';
import raw_specs from 'specs/swagger/raw.json';

// Mock the API and the Swagger specs
config.api_specs = 'http://localhost/api/1/swagger.json';

const xhr = sinon.useFakeXMLHttpRequest();
const requests = [];

xhr.onCreate = function(req) { requests.push(req); };

// Needed in the require form to preserve http mock
const API = require('../../js/api').default;

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
    // this.spec = specs;
    // this.build();
    this.buildFromSpec(specs);
};

/**
 * An helper function to set API definitions
 * @param  {Object} defs A Swagger model definitions
 */
API.constructor.prototype.mock_defs = function(defs) {
    const specs = $.extend(true, {}, raw_specs);

    specs.definitions = defs;
    this.mock_specs(specs);
};

export default API;
