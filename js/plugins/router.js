define(['director', 'logger'], function(director, log) {
    'use strict';

    return function(Vue, options) {
        options = options || {};

        var Router = Vue.extend({
            name: 'Router',
            data: function() {
                return {
                    prefix: options.prefix || '',
                    router: new director.Router(),
                    current_path: null,
                };
            },
            created: function() {
                this.router.configure({
                    strict: false,
                    html5history: true,
                    convert_hash_in_init: false,
                    // recurse: 'forward',
                    before: this.on_before_event.bind(this),
                    on:  this.on_on_event.bind(this),
                    after: this.on_after_event.bind(this),
                    notfound: this.on_notfound.bind(this)
                });
                // Register some common parameter type
                this.router.param('oid', /([0-9a-fA-F\\-]+)/);
            },
            computed: {
                current_route: function() {
                    if (this.current_path) {
                        return this.current_path.replace(this.prefix, '/').replace('//', '/');
                    }
                }
            },
            methods: {
                /**
                 * Route to the given route
                 */
                go: function(route) {
                    log.debug('Go to', route);
                    this.router.setRoute(this.to_path(route));
                },
                to_path: function(route) {
                    var path = (this.prefix + route).replace('//', '/');
                    if (path[0] !== '/') {
                        path = '/' + path;
                    }
                    return path;
                },
                update: function() {
                    this.current_path = '/' + this.router.getRoute().join('/');
                },
                on_before_event: function() {
                    this.callback('before');
                    this.$dispatch('route:changed:before', this);
                },
                on_on_event: function() {
                    this.update();
                    this.callback('on');
                    this.$dispatch('route:changed', this);
                },
                on_after_event: function() {
                    this.callback('after');
                    this.$dispatch('route:changed:after', this);
                },
                on: function(route, func) {
                    route = this.to_path(route);
                    this.router.on.apply(this.router, [route, func]);
                },
                on_notfound: function() {
                    this.update();
                    log.debug('Route not found', this.current_route);
                },
                callback: function(name) {
                    var option = this.$options[name],
                        callbacks;

                    if (!option) { return; }

                    callbacks = Vue.util.isArray(option) ? option : [option];

                    for (var i=0; i < callbacks.length; i++) {
                        callbacks[i].apply(this);
                    }
                },
                init: function() {
                    this.router.init();
                },
                /**
                 * Recursively bind routes to a given scope
                 * @param  {Object} routes a routing table to bind
                 * @param  {Object} scope  The scope to bind callbacks on
                 * @return {Object}        The binded routing table
                 */
                bind: function(routes, scope) {
                    for (var prop in routes){
                        if (Vue.util.isObject(routes[prop])) {
                            routes[prop] = this.bind(routes[prop], scope);
                        } else if (Vue.util.isFunction(routes[prop])) {
                            routes[prop] = Vue.util.bind(routes[prop], scope);
                        }
                    }
                    return routes;
                },

                mount: function(obj) {
                    // Bind routes
                    if (Object.getOwnPropertyNames(obj.$options.routes || {}).length > 0) {
                        var routes = this.bind(obj.$options.routes, obj);
                        this.router.mount(routes, this.prefix);
                    }
                }

            }
        });

        /**
         * Make the router object available globaly on Vue.route
         * and as instance property on this.$router.
         */
        Vue.prototype.$router = Vue.router = new Router();

        /**
         * Bind routes on init
         */
        var super_scope = Vue.prototype._initScope;
        Vue.prototype._initScope = function() {
            super_scope.apply(this);
            Vue.router.mount(this);
        };

        /**
         * Allow to route from everywhere:
         *  - on global scope with Vue.go
         *  - on instance scope with this.$go
         */
        Vue.prototype.$go = Vue.go = function(route) {
            return Vue.router.go(route);
        };

        /**
         * Allow to declare routes as component options
         */
        Vue.options.routes = {};

        /**
         * Allow to declare route for click event
         */
        Vue.directive('route', {
            isLiteral: true,
            bind: function() {
                this.route = this.expression;
                this.handler = function() {
                    Vue.go(this.route);
                }.bind(this);
                Vue.util.on(this.el, 'click', this.handler);
                if (!this.el.className.indexOf('pointer') >= 0) {
                    this.el.className += ' pointer';
                }
            },
            update: function(value) {
                this.route = value;
            },
            unbind: function() {
                Vue.util.off(this.el, 'click', this.handler);
            }
        });
    };
});


