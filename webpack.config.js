var path = require('path');
var webpack = require('webpack');

var ExtractTextPlugin = require('extract-text-webpack-plugin');
var node_path = path.join(__dirname, 'node_modules');
var vendor_path = path.join(__dirname, 'js', 'vendor');

var vue = require('vue-loader'),
    css_loader = ExtractTextPlugin.extract('style', 'css?sourceMap'),
    less_loader = ExtractTextPlugin.extract('style', 'css?sourceMap!less?sourceMap=source-map-less-inline'),
    html_loader = 'vue-html?collapseBooleanAttributes=false&collapseWhitespace=false"',
    js_loader = 'babel?optional[]=runtime&loose=all&nonStandard=false';

var languages = ['en', 'es', 'fr'];

module.exports = {
    entry: {
        admin: "./js/admin.js",
        site: './js/site.js',
        home: './js/home.js',
        search: './js/search.js',
        dashboard: './js/dashboard.js',
        'dataset/display': './js/dataset/display',
        'reuse/display': './js/reuse/display',
        'organization/display': './js/organization/display',
        'site/map': './js/site/map',
        'topic/display': './js/topic/display',
        'post/display': './js/post/display',
        'user/display': './js/user/display',
        'apidoc': './js/apidoc',
    },
    output: {
        path: path.join(__dirname, 'udata', 'static'),
        publicPath: "/static/",
        filename: "[name].js",
        chunkFilename: "[id].[hash].js"
    },
    resolve: {
        root: [
            __dirname,
            path.join(__dirname, 'js'),
        ],
        alias: {
            'jquery-slimscroll': path.join(node_path, 'jquery-slimscroll/jquery.slimscroll'),
            'fineuploader': path.join(node_path, 'fine-uploader/fine-uploader/fine-uploader'),
            'bloodhound': path.join(node_path, 'typeahead.js/dist/bloodhound'),
            'typeahead': path.join(node_path, 'typeahead.js/dist/typeahead.jquery'),
            'handlebars': 'handlebars/runtime.js',
            'swaggerui': 'swagger-ui/dist',
            'jquery': require.resolve('jquery')
        }
    },
    devtool: 'eval-source-map',
    module: {
        loaders: [
            {test: /\.(jpg|jpeg|png|gif|svg)$/, loader: 'file'},
            {test: /\.css$/, loader: css_loader},
            {test: /\.less$/, loader: less_loader},
            {test: /\.vue$/, loader: vue.withLoaders({
                html: html_loader,
                css: css_loader,
                less: less_loader,
                js: js_loader
            })},
            {test: /\.json$/, loader: "json"},
            {test: /\.hbs$/, loader: 'handlebars?debug=true&helperDirs[]=' + path.join(__dirname, 'js', 'templates', 'helpers')},
            {test: /\.html$/, loader: html_loader},
            {test: /\.(woff|svg|ttf|eot|otf)([\?]?.*)$/, loader: "file-loader?name=[name].[ext]"},
            {test: /\.js$/, loader: js_loader,
                include: [
                    path.resolve(__dirname, 'js'),
                    path.resolve(__dirname, 'specs'),
                ],
                exclude: path.resolve(__dirname, 'specs', 'loader.js')
            },
        ]
    },
    vue: {
        loaders: {
            html: html_loader,
            css: css_loader,
            less: less_loader,
            js: js_loader
        }
    },
    plugins: [
        // Fix AdminLTE packaging
        new webpack.NormalModuleReplacementPlugin(
            /admin-lte\/build\/img\/boxed-bg\.jpg$/,
            'admin-lte/dist/img/boxed-bg.jpg'
        ),
        // new webpack.ContextReplacementPlugin(/admin-lte\/build\/img\/.*$/, 'admin-lte/dist/img/$1'),
        new webpack.ProvidePlugin({
            $: 'jquery',
            jQuery: 'jquery',
            'window.jQuery': 'jquery',
        }),
        new ExtractTextPlugin('[name].css', {
            allChunks: true
        }),
        new webpack.IgnorePlugin(/^(\.\/)?shred/),
        new webpack.ContextReplacementPlugin(/moment\/locale$/, new RegExp(languages.join('|'))),
        new webpack.ContextReplacementPlugin(/locales$/, new RegExp(languages.join('|'))),
        new webpack.optimize.CommonsChunkPlugin("vue-common.js", ["admin", "dashboard"]),
        new webpack.optimize.CommonsChunkPlugin('common.js')
    ]
};
