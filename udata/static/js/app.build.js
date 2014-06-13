({
    appDir: './',

    baseUrl: './',

    dir: '../js-built',

    mainConfigFile: './config.js',

    skipDirOptimize: true,

    optimize: "uglify2",

    pragmas: {
        production:true
    },

    modules: [
        {
            name: "app",
            include: [
                'home',
                'dashboard/site',
                'dataset/display',
                'dataset/form',
                'dataset/resource-form',
                'form/extras',
                'organization/display',
                'organization/form',
                'organization/members',
                'organization/membership-requests',
                'reuse/display',
                'reuse/form',
                'search',
                'topic/display'
            ]
        }
    ]
})
