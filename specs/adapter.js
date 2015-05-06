
// window.assert = chai.assert;

// var should;
// (function(window) {
'use strict';

    // var path = require('path');

    // console.log(path.path.dirname(require.resolve('sinon')) + '/../pkg/sinon.js');

    var $ = require('jquery'),
        chai = require('chai'),
        sinon = require("imports?define=>false!sinon"),
        // sinon = require('sinon');
        // sinon = require(path.dirname(require.resolve('sinon')) + '/../pkg/sinon.js'),
        // sinon = require("sinon"),
        sinonChai = require('sinon-chai'),
        chaiJQuery = require('chai-jquery'),
        chaiThings = require('chai-things');
        // assert = chai.assert;

    // sinon.spy = require("sinon/lib/sinon/spy");
    // sinon.spyCall = require("sinon/lib/sinon/call");
    // sinon.behavior = require("sinon/lib/sinon/behavior");
    // sinon.stub = require("sinon/lib/sinon/stub");
    // sinon.mock = require("sinon/lib/sinon/mock");
    // sinon.collection = require("sinon/lib/sinon/collection");
    // sinon.assert = require("sinon/lib/sinon/assert");
    // sinon.sandbox = require("sinon/lib/sinon/sandbox");
    // sinon.test = require("sinon/lib/sinon/test");
    // sinon.testCase = require("sinon/lib/sinon/test_case");
    // sinon.match = require("sinon/lib/sinon/match");
    console.log(chai, sinon, expect);

    chai.use(sinonChai);
    chai.use(chaiThings);
    chai.use(chaiJQuery);

    window.expect = chai.expect;
    window.assert = chai.assert;
    window.sinon = sinon;

  // window.should = window.chai.should();
  // window.expect = window.chai.expect;
  // window.assert = window.chai.assert;
// })(window);


module.exports = {};
