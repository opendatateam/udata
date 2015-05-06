var path = require("path");
var webpack = require("webpack");

var ExtractTextPlugin = require("extract-text-webpack-plugin");
var BowerWebpackPlugin = require('bower-webpack-plugin');
var bower_path = path.join(__dirname, "bower_components");
var node_path = path.join(__dirname, "node_modules");

var languages = ['en', 'fr'];

module.exports = {
    entry: {
        admin: "./js/main.js",
        // iecompat: [
        //     'es5-shim',
        //     'es5-shim/es5-sham',
        //     'es6-shim',
        //     'es6-shim/es6-sham',
        //     'html5shiv/dist/html5shiv',
        //     // 'html5shiv/dist/html5shiv-printshiv.js',
        //     'imports?this=>window!respond.js/dest/respond.src'
        // ]
    },
    output: {
        path: path.join(__dirname, 'udata_admin', 'static'),
        publicPath: "/admin/static/",
        filename: "[name].js"
    },
    resolve: {
        root: [
            __dirname,
            path.join(__dirname, 'js'),
            bower_path,
        ],
        alias: {
            // 'jquery': path.join(bower_path, 'jquery/dist/jquery'),
            // 'bootstrapjs': path.join(bower_path, 'bootstrap/dist/js/bootstrap'),
            'Jcrop': path.join(bower_path, 'jcrop/js/jquery.Jcrop'),
            // 'swaggerjs': path.join(bower_path, 'swagger-js/lib/swagger-client'),
            'fineuploader': path.join(node_path, 'fine-uploader/fine-uploader/fine-uploader'),
            'jquery-validation': path.join(node_path, 'jquery-validation/src/core'),
            // 'bootstrap-datepicker': path.join(node_path, 'bootstrap-datepicker/js/bootstrap-datepicker'),
            // 'eve': path.join(bower_path, 'eve-adobe/eve')
        }
    },
    // devtools: 'source-map',
    devtools: 'eval-source-map',
    module: {
        loaders: [
            {test: /\.(jpg|jpeg|png|gif|svg)$/, loader: 'file'},
            {test: /\.css$/, loader: ExtractTextPlugin.extract("style", "css?sourceMap")},
            {test: /\.less$/, loader: ExtractTextPlugin.extract("style", "css?sourceMap!less?sourceMap=source-map-less-inline")},
            {test: /\.vue$/, loader: "vue"},
            {test: /\.json$/, loader: "json"},
            {test: /\.html$/, loader: "html"},
            {test: /\.(woff|svg|ttf|eot|otf)([\?]?.*)$/, loader: "file-loader?name=[name].[ext]"},
        ]
    },
    plugins: [
        new BowerWebpackPlugin({
            modulesDirectories: ['bower_components'],
            excludes: [/.*\.less/, 'raphael', 'jquery']
        }),
        new webpack.ResolverPlugin(
            new webpack.ResolverPlugin.DirectoryDescriptionFilePlugin("bower.json", ["main"])
        ),
        new webpack.NormalModuleReplacementPlugin(
            /iCheck\/minimal\/minimal\.png$/,
            'iCheck/skins/minimal/minimal.png'
        ),
        new webpack.NormalModuleReplacementPlugin(
            /iCheck\/minimal\/minimal@2x\.png$/,
            'iCheck/skins/minimal/minimal@2x.png'
        ),
        // Fix AdminLTE packaging
        new webpack.NormalModuleReplacementPlugin(
            /AdminLTE\/build\/img\/boxed-bg\.jpg$/,
            'AdminLTE/dist/img/boxed-bg.jpg'
        ),
        // new webpack.ContextReplacementPlugin(/AdminLTE\/build\/img\/.*$/, 'AdminLTE/dist/img/$1'),
        new webpack.ProvidePlugin({
            $: 'jquery',
            jQuery: 'jquery',
            'window.jQuery': 'jquery',
            'window.Raphael': 'raphael-browserify',
            Raphael: 'raphael-browserify'
        }),
        new ExtractTextPlugin('[name].css'),
        new webpack.IgnorePlugin(/^(\.\/)?shred/),
        // new webpack.IgnorePlugin(/btoa/),
        // new webpack.IgnorePlugin(/shred/),
        new webpack.ContextReplacementPlugin(/moment\/locale$/, new RegExp(languages.join('|')))
    ]
};
