/**
 * Generic site display page JS module
 */
import 'front/bootstrap';

// TODO: cleanup/refactorize less
import 'less/home.less';

import log from 'logger';
import Vue from 'vue';

// Legacy depdencies soon to be dropped
import $ from 'jquery';
import 'bootstrap';


new Vue({
    el: 'body',
    ready() {
        log.debug('Home page');
        $('.carousel').carousel();
    }
});
