/**
 * Reuse display page JS module
 */

// ES6 environment
import 'babel-polyfill';

import $ from 'jquery';
import log from 'logger';

import 'widgets/featured';
import 'widgets/follow-btn';
import 'widgets/issues-btn';
import 'widgets/discussions-btn';
import 'widgets/share-btn';

$(function() {
    log.debug('Reuse display page');
});
