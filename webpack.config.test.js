var webpack = require("webpack"),
    config = require('./webpack.config'),
    path = require('path'),
    languages = ['en', 'es', 'fr'];

var vue = require('vue-loader'),
    html_loader = 'html?collapseBooleanAttributes=false&collapseWhitespace=false"',
    js_loader = 'babel';


config.entry = 'mocha!specs/loader.js';
config.output = {
    filename: 'specs.min.js',
    path: path.join(__dirname, 'build'),
    publicPath: '/build/'
};

config.devServer = {
    hostname: 'localhost',
    port: 8080
};

config.module.loaders = [
    {test: /\.(jpg|jpeg|png|gif|svg)$/, loader: 'null'},
    {test: /\.css$/, loader: 'null'},
    {test: /\.less$/, loader: 'null'},
    {test: /\.(woff|svg|ttf|eot|otf)([\?]?.*)$/, loader: 'null'},
    {test: /\.vue$/, loader: vue.withLoaders({
        html: html_loader,
        css: 'null',
        less: 'null',
        js: js_loader
    })},
    {test: /\.json$/, loader: "json"},
    {test: /\.hbs$/, loader: 'handlebars?debug=true&helperDirs[]=' + path.join(__dirname, 'js', 'templates', 'helpers')},
    {test: /\.html$/, loader: html_loader},
    {test: /\.js$/, loader: js_loader,
        include: [
            path.resolve(__dirname, 'js'),
            path.resolve(__dirname, 'specs'),
        ],
        exclude: path.resolve(__dirname, 'specs', 'loader.js')
    },
];

// Fix SinonJS until proper 2.0
config.module.noParse = [/\/sinon.js/];
config.plugins.push(new webpack.NormalModuleReplacementPlugin(
    /^sinon$/,
    __dirname + '/node_modules/sinon/pkg/sinon.js'
));

// Export some globals
config.plugins.push(new webpack.ProvidePlugin({
    fixture: 'specs/fixture'
}));

module.exports = config;
