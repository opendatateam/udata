const path = require('path');
const webpack = require('webpack');

const node_path = path.join(__dirname, 'node_modules');
const theme_path = path.join(__dirname, 'udata_gouvfr', 'theme');
const static_path = path.join(theme_path, 'static');
const source_path = path.join(__dirname, 'theme');
const public_path = '/_themes/gouvfr/'

const ManifestPlugin = require('webpack-manifest-plugin');
const ExtractTextPlugin = require('extract-text-webpack-plugin');

// replaces the static URLs from less/css to public_path/*
const css_loader = ExtractTextPlugin.extract('style', 'css?root='+source_path+'&sourceMap');
const less_loader = ExtractTextPlugin.extract('style', 'css?root='+source_path+'&sourceMap!less?sourceMap=source-map-less-inline');
// const css_loader = ExtractTextPlugin.extract('vue-style?sourceMap', 'css?sourceMap');
// const less_loader = ExtractTextPlugin.extract('vue-style?sourceMap', 'css?sourceMap!less?sourceMap=source-map-less-inline');

const languages = ['en', 'es', 'fr', 'pt', 'sr'];

module.exports = {
    context: source_path,
    entry: {
        theme: "theme",
        admin: "admin",
        oembed: 'oembed',
        dataset: "js/front/dataset",
        territory: "js/front/territory",
        reuse: "js/front/reuse",
        site: "js/front/site.js",
        home: "js/front/home.js",
        search: "js/front/search.js",
        dashboard: "js/front/dashboard.js",
        organization: "js/front/organization",
        covermap: "js/front/covermap",
        topic: "js/front/topic",
        post: "js/front/post",
        user: "js/front/user",
    },
    output: {
        path: static_path,
        publicPath: public_path,
        filename: '[name].[hash].js',
        chunkFilename: 'chunks/[id].[chunkhash].js'
    },
    resolve: {
        root: [
            source_path,
            path.join(source_path, 'js'),
        ],
        alias: {
            'jquery-slimscroll': path.join(node_path, 'jquery-slimscroll/jquery.slimscroll'),
        }
    },
    devtool: 'eval-source-map',
    module: {
        loaders: [
            {test: /\.(jpg|jpeg|png|gif|svg)$/, loader: 'file-loader'},
            {test: /\.css$/, loader: css_loader},
            {test: /\.less$/, loader: less_loader},
            {test: /\.vue$/, loader: 'vue-loader'},
            {test: /\.json$/, loader: 'json-loader'},
            {test: /\.(woff|svg|ttf|eot|otf)([\?]?.*)$/, exclude: /img/, loader: 'file-loader?name=[name].[ext]'},
            {test: /\.js$/, loader: 'babel-loader', include: [
                    path.resolve(source_path, 'js'),
                    path.resolve(node_path, 'vue-strap/src'),
                ]
            }
        ]
    },
    vue: {
        loaders: {
            css: 'vue-style?sourceMap!css?sourceMap',
            less: 'vue-style?sourceMap!css?sourceMap!less?sourceMap=source-map-less-inline',
            js: 'babel-loader'
        }
    },
    babel: {
        presets: ['env'],
        comments: false,
        plugins: [
            ['transform-builtin-extend', {globals: ['Error']}],
            'transform-runtime',
        ]
    },
    // Store initial values for easier inheritance
    defaults: {
        languages,
    },
    plugins: [
        // Prevent webpack 1.x false positive
        require('webpack-fail-plugin'),
        new webpack.ProvidePlugin({
            jQuery: 'jquery',  // Required by bootstrap.js
            'window.jQuery': 'jquery',  // Required by swagger.js jquery client
        }),
        new ManifestPlugin({
            fileName: path.join(theme_path, 'manifest.json'),
            // Filter out chunks and source maps
            filter: ({name, isInitial, isChunk}) => !name.endsWith('.map') && (isInitial || !isChunk),
            publicPath: public_path,
        }),
        new ExtractTextPlugin('[name].[contenthash].css'),
        // Only include needed translations
        new webpack.ContextReplacementPlugin(/moment\/locale$/, new RegExp('^' + languages.join('|') + '$')),
        new webpack.ContextReplacementPlugin(/locales$/, new RegExp(languages.join('|'))),
        new webpack.optimize.CommonsChunkPlugin({
            name: 'common',
            minChunks: 10,  // (Modules must be shared between 10 entries)
        })
    ],
    node: {
        fs: 'empty',
        net: 'empty',
        tls: 'empty'
    }
};
