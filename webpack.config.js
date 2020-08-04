const path = require('path');
const webpack = require('webpack');

const ManifestPlugin = require('webpack-manifest-plugin');
const ExtractTextPlugin = require('extract-text-webpack-plugin');
const node_path = path.join(__dirname, 'node_modules');
const theme_path = path.join(__dirname, 'udata_gouvfr', 'theme');
const static_path = path.join(theme_path, 'static');
const source_path = path.join(__dirname, 'theme');
const public_path = '/_themes/gouvfr/'

const css_loader = ExtractTextPlugin.extract('style', 'css?root='+source_path+'&sourceMap');
const less_loader = ExtractTextPlugin.extract('style', 'css?root='+source_path+'&sourceMap!less?sourceMap=source-map-less-inline');


module.exports = {
    context: source_path,
    entry: {
        theme: "js/theme",
        admin: "js/admin",
        oembed: 'js/oembed',
        dataset: "js/dataset",
        territory: "js/territory",
        reuse: "js/reuse",
        site: "js/site.js",
        home: "js/home.js",
        search: "js/search.js",
        dashboard: "js/dashboard.js",
        organization: "js/organization",
        covermap: "js/covermap",
        topic: "js/topic",
        post: "js/post",
        user: "js/user",
    },
    output: {
        path: static_path,
        publicPath: public_path,
        filename: "[name].[hash].js",
        chunkFilename: 'chunks/[id].[hash].js'
    },
    resolve: {
        root: source_path,
        alias: {
            'jquery-slimscroll': path.join(node_path, 'jquery-slimscroll/jquery.slimscroll'),
        }
    },
    devtools: 'eval-source-map',
    module: {
        loaders: [
            {test: /\.(jpg|jpeg|png|gif|svg)$/, loader: 'file-loader'},
            {test: /\.css$/, loader: css_loader},
            {test: /\.less$/, loader: less_loader},
            {test: /\.vue$/, loader: 'vue-loader'},
            {test: /\.json$/, loader: 'json-loader'},
            {test: /\.(woff|svg|ttf|eot|otf)([\?]?.*)$/, exclude: /img/, loader: 'file-loader?name=[name].[ext]'},
            {test: /\.js$/, loader: 'babel-loader', include: [
                    path.resolve(__dirname, 'js'),
                    path.resolve(__dirname, 'node_modules/vue-strap/src'),
                ]
            }
        ]
    },
    babel: {
        presets: ['es2015'],
        comments: false,
        plugins: ['transform-runtime']
    },
    vue: {
        loaders: {
            css: 'vue-style?sourceMap!css?sourceMap',
            less: 'vue-style?sourceMap!css?sourceMap!less?sourceMap=source-map-less-inline',
            js: 'babel-loader'
        }
    },
    plugins: [
        new ManifestPlugin({
            fileName: path.join(theme_path, 'manifest.json'),
            // Filter out chunks and source maps
            filter: ({name, isInitial, isChunk}) => !name.endsWith('.map') && (isInitial || !isChunk),
            publicPath: public_path,
        }),
        new webpack.ProvidePlugin({
            jQuery: 'jquery',  // Required by bootstrap.js
        }),
        new ExtractTextPlugin('[name].[contenthash].css'),
        require('webpack-fail-plugin'),
    ]
};
