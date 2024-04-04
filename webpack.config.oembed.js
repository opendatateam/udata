const path = require('path');
const webpack = require('webpack');
const ExtractTextPlugin = require('extract-text-webpack-plugin');
const less_loader = ExtractTextPlugin.extract('vue-style?sourceMap', 'css?sourceMap!less?sourceMap=source-map-less-inline');

const config = {
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
                    presets: ['env'],
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
        new webpack.DefinePlugin({
            'process.env': {
                'NODE_ENV': JSON.stringify(process.env.NODE_ENV)
            }
        }),
    ],
};

if (process.env.NODE_ENV === 'production') {
    config.plugins.push(
        new webpack.optimize.UglifyJsPlugin({
            minimize: true,
            output: {
                comments: false,
                screw_ie8: true
            },
            mangle: {
                screw_ie8: true
            },
            compress: {
                warnings: false,
                screw_ie8: true
            }
        })
    );
} else {
    config.devtool = '#cheap-module-source-map';
}

module.exports = config;
