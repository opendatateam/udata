(function(window) {
    "use strict";

    var $ = require('jquery'),
        chai = require('chai'),
        sinon = require("sinon"),
        sinonChai = require("sinon-chai"),
        chaiJQuery = require("chai-jquery"),
        chaiThings = require("chai-things");

    chai.use(sinonChai);
    chai.use(chaiThings);
    chai.use(chaiJQuery);

    global.expect = window.expect = chai.expect;
    global.assert = window.assert = chai.assert;
    global.sinon = window.sinon = sinon;
    global.expect = window.$ = $;

})(window);
