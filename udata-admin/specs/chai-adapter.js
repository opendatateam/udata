(function(window) {
    "use strict";

    var $ = require('jquery'),
        chai = require('chai'),
        sinon = require("sinon"),
        sinonChai = require("sinon-chai"),
        chaiJQuery = require("chai-jquery"),
        chaiThings = require("chai-things");

    global.$ = window.$ = $;
    global.sinon = window.sinon = sinon;
    global.expect = window.expect = chai.expect;
    global.assert = window.assert = chai.assert;

    chai.use(sinonChai);
    chai.use(chaiJQuery);
    chai.use(chaiThings);

})(window);
