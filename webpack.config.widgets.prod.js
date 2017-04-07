var webpack = require('webpack');
var config = require('./webpack.config.widgets');

config.plugins = [new webpack.optimize.UglifyJsPlugin({
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
})];

config.devtool = 'source-map';

module.exports = config;
