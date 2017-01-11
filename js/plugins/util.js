export function install(Vue) {
    /**
     * Give the size of an array or a string
     */
    Vue.filter('length', function(value) {
        if (Array.isArray(value)) {
            return value.length;
        }
        return 0;
    });

    /**
     * Ensure a list is as list of IDs (unest if it's not the case)
     */
    Vue.filter('ids', function(list) {
        return list ? list.map(function(item) {
            return item.hasOwnProperty('id') ? item.id : item;
        }) : [];
    });

    /**
     * Find the better way to labelize an object
     */
    Vue.filter('display', function(object) {
        if (!object) {
            return;
        }
        if (object.title) {
            return object.title;
        } else if (object.name) {
            return object.name;
        } else if (object.fullname) {
            return object.fullname;
        } else if (object.first_name && object.last_name) {
            return object.first_name + ' ' + object.last_name;
        } else {
            return;
        }
    });

    /**
     * Test that object is a given domain model class
     */
    Vue.filter('is', function(obj, cls) {
        if (!obj || !cls) return;
        const classname = obj.__class__ || obj.class || obj.classname;
        return classname.toLowerCase() === cls.toLowerCase();
    });
}
