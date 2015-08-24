define(['jquery', 'api', 'events'], function($, API, ev) {
    'use strict';

    var menu = new ev.EventEmitter();

    menu.fetch = function() {
        API.admin.get_admin_menu({}, function(data) {
            $.extend(true, this, data.obj);
            this.emit('updated');
        }.bind(this));
    };

    if (API.isBuilt) {
        menu.fetch();
    } else {
        $(API).on('built', menu.fetch.bind(menu));
    }

    return menu;
});
