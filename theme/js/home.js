/**
 * Generic site display page JS module
 */
import FrontMixin from 'front/mixin';

// TODO: cleanup/refactorize less
import 'less/home.less';

import log from 'logger';
import Vue from 'vue';

// Legacy depdencies soon to be dropped
import $ from 'jquery';
import 'bootstrap';


new Vue({
    mixins: [FrontMixin],
    ready() {
        log.debug('Home page');
        $('.carousel').carousel();
    }
});
