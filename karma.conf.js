// Karma configuration
// Generated on Tue Dec 23 2014 19:11:34 GMT+0100 (CET)

var webpack_config = require('./webpack.config.js'),
    path = require('path');

webpack_config.debug = false;

webpack_config.devtool = 'inline-source-map';

// webpack_config.resolve.alias['sinon'] = path.dirname(require.resolve('sinon')) + '/../pkg/sinon.js';

// Instrumentate code with Istanbul for coverage
// webpack_config.module.postLoaders = [{
//     test: /\.(js|vue)$/,
//     exclude: /(specs|node_modules|bower_components)\//,
//     loader: 'istanbul-instrumenter'
// }];

var createPattern = function(path) {
    return {pattern: path, included: true, served: true, watched: false};
};

// var framework = function(files) {
// };

var files = [
        // createPattern('specs/adapter.js'),
        // createPattern(require.resolve('jquery')),
        // createPattern(path.dirname(require.resolve('chai')) + '/chai.js'),
        // createPattern(path.dirname(require.resolve('sinon')) + '/../pkg/sinon.js'),
        // createPattern(require.resolve('sinon-chai')),
        // createPattern(require.resolve('chai-jquery')),
        // createPattern(require.resolve('chai-things')),
        'specs/**/*.specs.js'
    ],
    preprocessors = {};

files.forEach(function(file) {
    preprocessors[file] = ['webpack', 'sourcemap'];
});

console.log(preprocessors);


module.exports = function(config) {
    config.set({

        // base path that will be used to resolve all patterns (eg. files, exclude)
        basePath: '',


        // frameworks to use
        // available frameworks: https://npmjs.org/browse/keyword/karma-adapter
        frameworks: ['mocha', 'chai', 'sinon-chai', 'chai-jquery', 'fixture'],
        // frameworks: ['mocha', 'chai-things', 'jquery-chai', 'chai-sinon', 'fixture'],
        // frameworks: ['mocha', 'fixture'],

        // files: [
        //   'specs/loader.js' //just load this file
        // ],
        // preprocessors: {
        //   'specs/loader.js': [ 'webpack', 'sourcemap' ] //preprocess with webpack and our sourcemap loader
        // },
        //
        files: [
          'specs/**/*.specs.js' //just load this file
        ],
        preprocessors: {
          'specs/**/*.specs.js': [ 'webpack', 'sourcemap' ] //preprocess with webpack and our sourcemap loader
        },

        // list of files / patterns to load in the browser
        // files: [
        //     createPattern(require.resolve('jquery')),
        //     createPattern(path.dirname(require.resolve('chai')) + '/chai.js'),
        //     createPattern(path.dirname(require.resolve('sinon')) + '/../pkg/sinon.js'),
        //     createPattern(require.resolve('sinon-chai')),
        //     createPattern(require.resolve('chai-jquery')),
        //     createPattern(require.resolve('chai-things')),
        //     // 'specs/chai-adapter.js',
        //     'specs/**/*.specs.js'
        // ],
        // files: [
        //     // createPattern(require.resolve('jquery')),
        //     // createPattern(path.dirname(require.resolve('chai')) + '/chai.js'),
        //     // createPattern(path.dirname(require.resolve('sinon')) + '/../pkg/sinon.js'),
        //     // createPattern(require.resolve('sinon-chai')),
        //     // createPattern(require.resolve('chai-jquery')),
        //     // createPattern(require.resolve('chai-things')),
        //     // createPattern('specs/adapter.js'),
        //     // 'specs/adapter.js',
        //     //
        //     'specs/**/*.specs.js'
        // ],
        // files: files,


        // list of files to exclude
        exclude: [
        ],


        // preprocess matching files before serving them to the browser
        // available preprocessors: https://npmjs.org/browse/keyword/karma-preprocessor
        // preprocessors: {
        //     'specs/adapter.js': ['webpack'],
        //     // scpath: ['webpack'],
        //     'specs/**/*.specs.js': ['webpack', 'sourcemap']
        // },
        // preprocessors: preprocessors,

        webpack: webpack_config,

        webpackServer : {
            quiet: true
        },


        // test results reporter to use
        // possible values: 'dots', 'progress'
        // available reporters: https://npmjs.org/browse/keyword/karma-reporter
        reporters: ['mocha', 'coverage'],

        client: {
            mocha: {
                reporter: 'html', // change Karma's debug.html to the mocha web reporter
            }
        },

        coverageReporter: {
            type: 'lcov',
            dir: 'coverage/'
        },


        // web server port
        port: 9876,


        // enable / disable colors in the output (reporters and logs)
        colors: true,


        // level of logging
        // possible values: config.LOG_DISABLE || config.LOG_ERROR || config.LOG_WARN || config.LOG_INFO || config.LOG_DEBUG
        logLevel: config.LOG_INFO,


        // enable / disable watching file and executing tests whenever any file changes
        autoWatch: true,


        // start these browsers
        // available browser launchers: https://npmjs.org/browse/keyword/karma-launcher
        // browsers: ['Chrome'], //, 'Firefox', 'PhantomJS'],
        // browsers: ['PhantomJS'],

        // Continuous Integration mode
        // if true, Karma captures browsers, runs the tests and exits
        singleRun: false,

        plugins: [
            require('karma-webpack'),
            require('karma-mocha'),
            require('karma-mocha-reporter'),
            require('karma-phantomjs-launcher'),
            require('karma-sourcemap-loader'),
            require('karma-chai-plugins'),
            require('karma-fixture'),
            require('karma-coverage')
        ]

    });
};
