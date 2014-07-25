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
                'dataset/display',
                'organization/display',
                'reuse/display',
                'topic/display'
            ]
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
        }
    ]
})
