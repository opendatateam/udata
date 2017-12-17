const path = require('path');
const webpack = require('webpack');

const ExtractTextPlugin = require('extract-text-webpack-plugin');
const node_path = path.join(__dirname, 'node_modules');

const css_loader = ExtractTextPlugin.extract('vue-style?sourceMap', 'css?sourceMap');
const less_loader = ExtractTextPlugin.extract('vue-style?sourceMap', 'css?sourceMap!less?sourceMap=source-map-less-inline');

const languages = ['en', 'es', 'fr'];

module.exports = {
    entry: {
        admin: './js/admin.js',
        dataset: './js/front/dataset',
        territory: './js/front/territory',
        reuse: './js/front/reuse',
        site: './js/front/site.js',
        home: './js/front/home.js',
        search: './js/front/search.js',
        dashboard: './js/front/dashboard.js',
        apidoc: './js/front/apidoc',
        organization: './js/front/organization',
        covermap: './js/front/covermap',
        topic: './js/front/topic',
        post: './js/front/post',
        user: './js/front/user',
    },
    output: {
        path: path.join(__dirname, 'udata', 'static'),
        publicPath: '/static/',
        filename: '[name].js',
        chunkFilename: 'chunks/[id].[hash].js'
    },
    resolve: {
        root: [
            __dirname,
            path.join(__dirname, 'js'),
        ],
        alias: {
            'jquery-slimscroll': path.join(node_path, 'jquery-slimscroll/jquery.slimscroll'),
            'swaggerui': 'swagger-ui/dist',
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
                    path.resolve(__dirname, 'js'),
                    path.resolve(__dirname, 'node_modules/vue-strap/src'),
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
        presets: ['es2015'],
        comments: false,
        plugins: ['transform-runtime']
    },
    // Store initial values for easier inheritance
    defaults: {
        languages,
    },
    plugins: [
        // Prevent webpack 1.x false positive
        require('webpack-fail-plugin'),
        // Fix AdminLTE packaging
        new webpack.NormalModuleReplacementPlugin(
            /admin-lte\/build\/img\/boxed-bg\.jpg$/,
            'admin-lte/dist/img/boxed-bg.jpg'
        ),
        new webpack.ProvidePlugin({
            jQuery: 'jquery',  // Required by bootstrap.js
            'window.jQuery': 'jquery',  // Required by swagger.js jquery client
        }),
        new ExtractTextPlugin('[name].css'),
        // Only include needed translations
        new webpack.ContextReplacementPlugin(/moment\/locale$/, new RegExp('^' + languages.join('|') + '$')),
        new webpack.ContextReplacementPlugin(/locales$/, new RegExp(languages.join('|'))),
        new webpack.optimize.CommonsChunkPlugin({
            name: 'common',
            filename: 'common.js',
            minChunks: 10,  // (Modules must be shared between 10 entries)
        })
    ],
    node: {
        fs: 'empty',
        net: 'empty',
        tls: 'empty'
    }
};
