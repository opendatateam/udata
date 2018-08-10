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
        theme: "theme",
        admin: "admin",
        oembed: 'oembed',
    },
    output: {
        path: static_path,
        publicPath: public_path,
        filename: "[name].[hash].js",
        chunkFilename: 'chunks/[id].[hash].js'
    },
    resolve: {
        root: source_path
    },
    devtools: 'eval-source-map',
    module: {
        loaders: [
            {test: /img\/.*\.(jpg|jpeg|png|gif|svg)$/, loader: 'file?name=[path][name].[ext]'},
            {test: /\.css$/, loader: css_loader},
            {test: /\.less$/, loader: less_loader},
            {test: /\.json$/, loader: "json"},
            {test: /\.html$/, loader: "html"},
            {test: /\.(woff|svg|ttf|eot|otf)([\?]?.*)$/, exclude: /img/, loader: "file?name=[name].[ext]"},
            {test: /\.js$/, loader: 'babel-loader', include: [
                    path.resolve(source_path, 'js'),
                ]
            }
        ]
    },
    babel: {
        presets: ['es2015'],
        comments: false,
        plugins: ['transform-runtime']
    },
    plugins: [
        new ManifestPlugin({
            fileName: path.join(theme_path, 'manifest.json'),
            // Filter out chunks and source maps
            filter: ({name, isInitial, isChunk}) => !name.endsWith('.map') && (isInitial || !isChunk),
            publicPath: public_path,
        }),
        new ExtractTextPlugin('[name].[contenthash].css'),
        require('webpack-fail-plugin'),
    ]
};
