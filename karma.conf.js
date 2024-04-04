// Karma configuration
// Generated on Tue Dec 23 2014 19:11:34 GMT+0100 (CET)

const webpack = require('webpack');
const path = require('path');

const ROOT = __dirname;

const WATCH = Boolean(process.env.WATCH);
const REPORT_DIR = process.env.REPORT_DIR || 'reports/karma';

module.exports = function(config) {
    config.set({

        // base path that will be used to resolve all patterns (eg. files, exclude)
        basePath: '',

        // frameworks to use
        // available frameworks: https://npmjs.org/browse/keyword/karma-adapter
        frameworks: ['mocha', 'sinon-chai', 'fixture'],

        files: [
            './specs/loader.js',  // Mocha specs
            './specs/fixtures/**/*',  // Fixtures
        ],
        preprocessors: {
            './specs/loader.js': ['webpack', 'sourcemap'],
            './specs/fixtures/**/*.html': ['html2js'],
        },

        // list of files to exclude
        exclude: [],

        webpack: {
            resolve: {
                root: [
                    ROOT,
                    path.join(ROOT, 'js'),
                ],
                alias: {
                    'api': 'specs/mocks/api',
                }
            },
            watch: WATCH,
            devtool: 'inline-source-map',
            module: {
                loaders: [
                    {test: /\.(jpg|jpeg|png|gif|svg)$/, loader: 'null-loader'},
                    {test: /\.css$/, loader: 'null-loader'},
                    {test: /\.less$/, loader: 'null-loader'},
                    {test: /\.vue$/, loader: 'vue-loader'},
                    {test: /\.json$/, loader: 'json-loader'},
                    {test: /\.(woff|svg|ttf|eot|otf)([\?]?.*)$/, exclude: /img/, loader: 'null-loader'},
                    {test: /\.js$/, exclude: /node_modules/, loader: 'babel-loader'},
                ]
            },
            vue: {
                loaders: {
                    css: 'null-loader',
                    less: 'null-loader'
                }
            },
            babel: {
                presets: ['env'],
                comments: false,
                plugins: [
                    ['transform-builtin-extend', {globals: ['Error']}],
                ],
            },
            plugins: [
                new webpack.IgnorePlugin(/moment\/locale\/.*/),
                new webpack.IgnorePlugin(/faker\/lib\/locales\/.*/),
                new webpack.ProvidePlugin({
                    $: 'jquery',
                    jQuery: 'jquery',
                    'window.jQuery': 'jquery',
                }),
            ]
        },

        webpackMiddleware: {noInfo: true},

        // test results reporter to use
        // possible values: 'dots', 'progress', 'specs'
        // available reporters: https://npmjs.org/browse/keyword/karma-reporter
        reporters: ['mocha'],

        // See here for all options: https://www.npmjs.com/package/karma-mocha-reporter
        mochaReporter: {
            showDiff: true,
        },

        client: {
            // captureConsole: true,
            // See here for all options: https://github.com/karma-runner/karma-mocha
            mocha: {
                reporter: 'html', // change Karma's debug.html to the mocha web reporter
            }
        },

        // See here for all options: https://github.com/karma-runner/karma-junit-reporter
        junitReporter: {
            outputDir: REPORT_DIR, // results will be saved as $outputDir/$browserName.xml
        },

        // web server port
        port: 9876,

        // enable / disable colors in the output (reporters and logs)
        colors: true,

        // level of logging
        // possible values: config.LOG_DISABLE || config.LOG_ERROR || config.LOG_WARN || config.LOG_INFO || config.LOG_DEBUG
        logLevel: config.LOG_INFO,

        // start these browsers
        // available browser launchers: https://npmjs.org/browse/keyword/karma-launcher
        // browsers: ['Chrome', 'Firefox', 'PhantomJS']
        browsers: ['PhantomJS'],

        // Continuous Integration mode
        // if true, Karma captures browsers, runs the tests and exits
        singleRun: false,

        plugins: [
            require('karma-webpack'),
            require('karma-mocha'),
            require('karma-mocha-reporter'),
            require('karma-phantomjs-launcher'),
            require('karma-firefox-launcher'),
            require('karma-chrome-launcher'),
            require('karma-ievms'),
            require('karma-sourcemap-loader'),
            require('karma-fixture'),
            require('karma-sinon-chai'),
            require('karma-junit-reporter'),
            require('karma-html2js-preprocessor'),
        ]

    });
};
