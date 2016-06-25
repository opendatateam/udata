const path = require('path');
const webpack = require('webpack');

const ExtractTextPlugin = require('extract-text-webpack-plugin');
const node_path = path.join(__dirname, 'node_modules');

const css_loader = ExtractTextPlugin.extract('style', 'css?sourceMap');
const less_loader = ExtractTextPlugin.extract('style', 'css?sourceMap!less?sourceMap=source-map-less-inline');
const handlebars_helpers = path.join(__dirname, 'js', 'templates', 'helpers');
const hbs_loader = `handlebars?helperDirs[]=${handlebars_helpers}`;

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
        dashboard: './js/dashboard.js',
        apidoc: './js/apidoc',
        organization: './js/front/organization',
        'site/map': './js/site/map',
        topic: './js/front/topic',
        post: './js/front/post',
        'user/display': './js/user/display',
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
            'bloodhound': path.join(node_path, 'corejs-typeahead/dist/bloodhound'),
            'typeahead': path.join(node_path, 'corejs-typeahead/dist/typeahead.jquery'),
            'handlebars': 'handlebars/runtime',
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
            {test: /\.vue$/, loader: 'vue'},
            {test: /\.json$/, loader: 'json'},
            {test: /\.hbs$/, loader: hbs_loader},
            {test: /\.(woff|svg|ttf|eot|otf)([\?]?.*)$/, exclude: /img/, loader: 'file-loader?name=[name].[ext]'},
            {test: /\.js$/, exclude: /node_modules/, loader: 'babel'},
        ]
    },
    vue: {
        loaders: {
            css: css_loader,
            less: less_loader,
            js: 'babel'
        }
    },
    babel: {
        presets: ['es2015'],
        comments: false,
        plugins: ['transform-runtime']
    },
    // Store initial values for easier inheritance
    defaults: {
        hbs_loader,
        languages,
    },
    plugins: [
        // Fix AdminLTE packaging
        new webpack.NormalModuleReplacementPlugin(
            /admin-lte\/build\/img\/boxed-bg\.jpg$/,
            'admin-lte/dist/img/boxed-bg.jpg'
        ),
        new webpack.ProvidePlugin({
            $: 'jquery',
            jQuery: 'jquery',
            'window.jQuery': 'jquery',
        }),
        new ExtractTextPlugin('[name].css'),
        new webpack.IgnorePlugin(/^(\.\/)?shred/),
        // Only include needed translations
        new webpack.ContextReplacementPlugin(/moment\/locale$/, new RegExp('^' + languages.join('|') + '$')),
        new webpack.ContextReplacementPlugin(/locales$/, new RegExp(languages.join('|'))),
        new webpack.optimize.CommonsChunkPlugin({
            name: 'common',
            filename: 'common.js',
            minChunks: 10,  // (Modules must be shared between 10 entries)
        })
    ]
};
