// ES6 environment
import 'babel-polyfill';

import $ from 'jquery';
import log from 'logger';
import Map from 'dashboard/map';

const map = new Map('.big-map');

$(function() {
    log.debug('Loading map');
    map.load();
});
