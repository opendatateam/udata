<template>
<div class="card user-card"
    :class="{ 'pointer': clickable, 'selected': selected }" @click="click">
    <a class="card-logo">
        <img :alt="user | display" :src="user | avatar_url 60">
    </a>
    <div class="card-body">
        <h4>
            <a :title="user | display">
                {{ user | display }}
            </a>
        </h4>

        <div class="clamp-3">{{{ user.about | markdown 180 }}}</div>
    </div>

    <footer v-if="user.metrics" class="card__footer">
        <ul>
            <li v-tooltip :title="_('Datasets')">
                <span class="fa fa-cubes fa-fw"></span>
                {{ user.metrics.datasets || 0 }}
            </li>
            <li v-tooltip :title="_('Reuses')">
                <span class="fa fa-retweet fa-fw"></span>
                {{ user.metrics.reuses || 0 }}
            </li>
            <li v-tooltip :title="_('Followers')">
                <span class="fa fa-star fa-fw"></span>
                {{ user.metrics.followers || 0 }}
            </li>
        </ul>
    </footer>
</div>
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
            default: true
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
