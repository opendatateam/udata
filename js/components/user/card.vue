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
    </div>
    <footer v-if="user.metrics">
        <ul>
            <li>
                <a class="btn btn-xs" v-tooltip tooltip-placement="top"
                    :title="_('Datasets')">
                    <span class="fa fa-cubes fa-fw"></span>
                    {{ user.metrics.datasets || 0 }}
                </a>
            </li>
            <li>
                <a class="btn btn-xs" v-tooltip tooltip-placement="top"
                    :title="_('Reuses')">
                    <span class="fa fa-retweet fa-fw"></span>
                    {{ user.metrics.reuses || 0 }}
                </a>
            </li>
            <li>
                <a class="btn btn-xs" v-tooltip tooltip-placement="top"
                    :title="_('Followers')">
                    <span class="fa fa-star fa-fw"></span>
                    {{ user.metrics.followers || 0 }}
                </a>
            </li>
        </ul>
    </footer>

    <a v-if="user.about" class="rollover fade in"
        :title="user | display">
        {{{ user.about | markdown 180 }}}
    </a>
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
