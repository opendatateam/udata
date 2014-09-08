({
    appDir: './',

    baseUrl: './',

    dir: '../js-built',

    mainConfigFile: './config.js',

    skipDirOptimize: true,

    optimize: "uglify2",

    generateSourceMaps: true,

    preserveLicenseComments: false,

    pragmas: {
        production:true
    },

    modules: [
        {
            name: "app"
        }, {
            name: 'dataset/display',
            exclude: [
                'app'
            ],
        }, {
            name: 'reuse/display',
            exclude: [
                'app'
            ],
        }, {
            name: 'organization/display',
            exclude: [
                'app'
            ],
        }, {
            name: 'topic/display',
            exclude: [
                'app'
            ],
        }, {
            name: 'form/widgets',
            exclude: [
                'app'
            ],
        }, {
            name: 'dashboard/site',
            exclude: [
                'app'
            ],
        }, {
            name: 'home',
            exclude: [
                'app'
            ],
        }, {
            name: 'search',
            exclude: [
                'app'
            ],
        }, {
            name: 'dataset/form',
            exclude: [
                'app',
                'form/widgets'
            ],
        }, {
            name: 'dataset/resource-form',
            exclude: [
                'app',
                'form/widgets'
            ],
        }, {
            name: 'form/extras',
            exclude: [
                'app',
                'form/widgets'
            ],
        }, {
            name: 'organization/form',
            exclude: [
                'app',
                'form/widgets'
            ],
        }, {
            name: 'organization/members',
            exclude: [
                'app',
                'form/widgets'
            ],
        }, {
            name: 'organization/membership-requests',
            exclude: [
                'app'
            ],
        }, {
            name: 'reuse/form',
            exclude: [
                'app',
                'form/widgets'
            ],
        }, {
            name: 'user/form',
            exclude: [
                'app',
                'form/widgets'
            ],
        }, {
            name: 'apidoc',
            exclude: [
                'app',
            ],
        }, {
            name: 'site/map',
            exclude: [
                'app',
            ],
        }, {
            name: 'issue/list',
            exclude: [
                'app',
            ],
        }
    ]
})
