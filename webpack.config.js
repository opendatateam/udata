const path = require('path');
const webpack = require('webpack');

const ExtractTextPlugin = require('extract-text-webpack-plugin');
const node_path = path.join(__dirname, 'node_modules');

const css_loader = ExtractTextPlugin.extract('style', 'css?sourceMap');
const less_loader = ExtractTextPlugin.extract('style', 'css?sourceMap!less?sourceMap=source-map-less-inline');
const js_loader = 'babel?presets[]=es2015';
const handlebars_helpers = path.join(__dirname, 'js', 'templates', 'helpers');
const hbs_loader = `handlebars?helperDirs[]=${handlebars_helpers}`;

const languages = ['en', 'es', 'fr'];

module.exports = {
    entry: {
        admin: './js/admin.js',
        site: './js/site.js',
        home: './js/home.js',
        search: './js/search.js',
        dashboard: './js/dashboard.js',
        apidoc: './js/apidoc',
        'dataset/display': './js/dataset/display',
        'reuse/display': './js/reuse/display',
        'organization/display': './js/organization/display',
        'site/map': './js/site/map',
        'topic/display': './js/topic/display',
        'post/display': './js/post/display',
        'user/display': './js/user/display',
    },
    output: {
        path: path.join(__dirname, 'udata', 'static'),
        publicPath: '/static/',
        filename: '[name].js',
        chunkFilename: '[id].[hash].js'
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
            {test: /\.(woff|svg|ttf|eot|otf)([\?]?.*)$/, loader: 'file-loader?name=[name].[ext]'},
            {test: /\.js$/, exclude: /node_modules/, loader: js_loader},
        ]
    },
    vue: {
        loaders: {
            css: css_loader,
            less: less_loader,
        }
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
        new ExtractTextPlugin('[name].css', {
            allChunks: true
        }),
        new webpack.IgnorePlugin(/^(\.\/)?shred/),
        // Only include needed translations
        new webpack.ContextReplacementPlugin(/moment\/locale$/, new RegExp('^' + languages.join('|') + '$')),
        new webpack.ContextReplacementPlugin(/locales$/, new RegExp(languages.join('|'))),
        new webpack.optimize.CommonsChunkPlugin('vue-common.js', ['admin', 'dashboard']),
        new webpack.optimize.CommonsChunkPlugin('common.js')
    ]
};
