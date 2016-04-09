import log from 'logger';
import User from 'models/user';
import Raven from 'raven';

class Me extends User {
    fetch() {
        this.$api('me.get_me', {}, this.on_user_fetched);
        return this;
    }

    update(data, on_success, on_error) {
        this.$api('me.update_me', {payload: JSON.stringify(data)}, on_success, on_error);
    }

    on_user_fetched(response) {
        Raven.setUserContext({
            id: response.obj.id,
            email: response.obj.email,
            slug: response.obj.slug,
            fullname: `${response.obj.first_name} ${response.obj.last_name}`,
            is_authenticated: true,
            is_anonymous: false
        });
        this.on_fetched(response);
    }
}

var me = new Me();

export default me.fetch();
