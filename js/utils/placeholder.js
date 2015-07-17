define(['site/config'], function(config) {
	return function(type) {
		return config.static_root + 'img/placeholders/' + type + '.png';
	}
});
