import log from 'logger';
import User from 'models/user';
import Raven from 'raven';

class Me extends User {
    fetch() {
        this.$api('me.get_me', {}, this.on_user_fetched);
        return this;
    }

    on_user_fetched(response) {
        Raven.setUserContext({
            id: response.obj.id,
            email: response.obj.email,
            slug: response.obj.slug,
            fullname: [response.obj.first_name, response.obj.last_name].join(' '),
            is_authenticated: true,
            is_anonymous: false
        });
        this.on_fetched(response);
    }
}

var me = new Me();

export default me.fetch();
