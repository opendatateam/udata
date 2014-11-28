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
            name: "app",
            include: [
                'form/widgets'
            ]
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
            ],
        }, {
            name: 'dataset/resource-form',
            exclude: [
                'app',
            ],
        }, {
            name: 'form/extras',
            exclude: [
                'app',
            ],
        }, {
            name: 'organization/form',
            exclude: [
                'app',
            ],
        }, {
            name: 'organization/members',
            exclude: [
                'app',
            ],
        }, {
            name: 'organization/membership-requests',
            exclude: [
                'app'
            ],
        }, {
            name: 'dashboard/organization',
            exclude: [
                'app'
            ],
        }, {
            name: 'reuse/form',
            exclude: [
                'app',
            ],
        }, {
            name: 'user/form',
            exclude: [
                'app',
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
            name: 'site/form',
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
