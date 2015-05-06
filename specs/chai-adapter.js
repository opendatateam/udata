
// window.assert = chai.assert;

// var should;
(function(window) {
"use strict";

var chai = require('chai'),
    sinon = require("sinon"),
    sinonChai = require("sinon-chai"),
    chaiJQuery = require("chai-jquery"),
    chaiThings = require("chai-things"),
    expect = chai.expect;
    // assert = chai.assert;

console.log(chai, sinon, expect);

chai.use(sinonChai);
chai.use(chaiThings);
chai.use(chaiJQuery);

window.expect = expect;
window.sinon = sinon;

  // window.should = window.chai.should();
  // window.expect = window.chai.expect;
  // window.assert = window.chai.assert;
})(window);


module.exports = {};
