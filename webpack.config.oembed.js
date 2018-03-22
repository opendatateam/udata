const path = require('path');
const ExtractTextPlugin = require('extract-text-webpack-plugin');
const less_loader = ExtractTextPlugin.extract('vue-style?sourceMap', 'css?sourceMap!less?sourceMap=source-map-less-inline');

module.exports = {
    entry: './js/oembed',
    output: {
        path: path.join(__dirname, 'udata', 'static'),
        publicPath: '/static/',
        filename: 'oembed.js',
    },
    module: {
        loaders: [
            {test: /\.less$/, loader: less_loader},
            {test: /\.(woff|svg|ttf|eot|otf)([\?]?.*)$/, exclude: /img/, loader: 'file-loader?name=[name].[ext]'},
            {
                test: /\.js$/,
                loader: 'babel-loader',
                query: {
                    presets: ['es2015'],
                    comments: false
                }
            },
        ]
    },
    node: {
        fs: 'empty',
        net: 'empty',
        tls: 'empty'
    },
    plugins: [
        // Prevent webpack 1.x false positive
        require('webpack-fail-plugin'),
        new ExtractTextPlugin('oembed.css'),
    ],
};
