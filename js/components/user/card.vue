<template>
<a class="card user-card" :class="{ selected: selected }" :title="user | display"
    :href="clickable" @click.prevent="click">
    <div class="card-logo">
        <img :alt="user | display" :src="user | avatar_url 60">
    </div>
    <div class="card-body">
        <h4>{{ user | display }}</h4>
        <div class="clamp-3">{{{ user.about | markdown 180 }}}</div>
    </div>

    <footer v-if="user.metrics" class="card-footer">
        <ul>
            <li v-tooltip :title="_('Datasets')">
                <span class="fa fa-cubes fa-fw"></span>
                {{ user.metrics.datasets || 0 }}
            </li>
            <li v-tooltip :title="_('Reuses')">
                <span class="fa fa-recycle fa-fw"></span>
                {{ user.metrics.reuses || 0 }}
            </li>
            <li v-tooltip :title="_('Followers')">
                <span class="fa fa-star fa-fw"></span>
                {{ user.metrics.followers || 0 }}
            </li>
        </ul>
    </footer>
</a>
</template>

<script>
import User from 'models/user';

export default {
    props: {
        user: {
            type: Object,
            default: () => new User(),
        },
        userid: null,
        clickable: {
            type: Boolean,
            default: false
        },
        selected: {
            type: Boolean,
            default: false
        }
    },
    created() {
        if (this.userid) {
            this.user.fetch(this.userid);
        }
    },
    methods: {
        click() {
            if (this.clickable) {
                this.$dispatch('user:clicked', this.user);
            }
        }
    }
};
</script>
