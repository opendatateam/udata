define(['site/config'], function(config) {
	console.log('static', config.static_root);
	return function(type) {
		return config.static_root + 'img/placeholders/' + type + '.png';
	}
});
