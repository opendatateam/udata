var webpack = require('webpack');
var config = require('./webpack.config.widgets');

config.plugins = [new webpack.optimize.UglifyJsPlugin({
    minimize: true,
    output: {comments: false},
    compress: {
        warnings: true
    }
})];

config.devtool = 'source-map';

module.exports = config;
