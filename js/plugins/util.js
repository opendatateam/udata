import $ from 'jquery';
import u from 'utils';

export default function(Vue, options) {  // jshint ignore:line

    /**
     * Check if an object is a Function
     */
    Vue.util.isFunction = u.isFunction;

    /**
     * Check if an object is a String
     */
    Vue.util.isString = u.isString;

    /**
     * Fetch the class name for given Vue object instance
     * @param  {Object} cls a Vue instance
     * @return {string}     The class name, declared or inherited
     */
    Vue.util.classname = function(cls) {
        var constructor = cls.constructor;
        while (constructor.name == 'VueComponent') {
            constructor = constructor.super;
        }
        return constructor.name
    }

    /**
     * Give the size of an array or a string
     */
    Vue.filter('length', function(value) {
        if (Vue.util.isArray(value)) {
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
            return object.name
        } else if (object.fullname) {
            return object.fullname;
        } else if (object.first_name && object.last_name) {
            return object.first_name + ' ' + object.last_name;
        } else {
            return;
        }
    });

    Vue.filter('is', function(obj, cls) {
        if (!obj) return;

        var classname = obj.class || obj.classname || Vue.util.classname(obj);

        return classname.toLowerCase() == cls.toLowerCase();
    })

    Vue.filter('cls', function(obj) {
        if (!obj) return;

        return obj.class || obj.classname || Vue.util.classname(obj);
    })
};
