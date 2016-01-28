var path = require('path');
var webpack = require('webpack');
var js_loader = 'babel?presets[]=es2015';

module.exports = {
    entry: {
        widgets: './js/widgets.js',
    },
    output: {
        path: path.join(__dirname, 'udata', 'static'),
        publicPath: '/static/',
        filename: 'widgets.js',
    },
    module: {
        loaders: [
            {test: /\.js$/, loader: js_loader},
        ]
    },

};
