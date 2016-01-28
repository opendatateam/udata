import config from 'config';

export default function(type) {
	return config.static_root + 'img/placeholders/' + type + '.png';
}
