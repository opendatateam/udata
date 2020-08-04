<template>
<a class="card organization-card" :class="{ selected: selected }" :title="organization.name"
    :href="clickable" @click.prevent="click">
    <div class="card-logo">
        <img :alt="organization.name" :src="logo">
    </div>

    <img v-if="organization.public_service"
        :src="certified_stamp" alt="certified" class="certified"
        v-popover="_('The identity of this public service is certified by %(certifier)s', certifier=config.SITE_AUTHOR)"
        :popover-title="_('Certified public service')"
        popover-trigger="hover"/>

    <div class="card-body">
        <h4>{{ organization.name }}</h4>
        <div class="clamp-3">{{{ organization.description | markdown 180 }}}</div>
    </div>

    <footer v-if="organization.metrics" class="card-footer">
        <ul>
            <li v-tooltip :title="_('Datasets')">
                <span class="fa fa-cubes fa-fw"></span>
                {{ organization.metrics.datasets || 0 }}
            </li>
            <li v-tooltip :title="_('Reuses')">
                <span class="fa fa-recycle fa-fw"></span>
                {{ organization.metrics.reuses || 0 }}
            </li>
            <li v-tooltip :title="_('Followers')">
                <span class="fa fa-star fa-fw"></span>
                {{ organization.metrics.followers || 0 }}
            </li>
        </ul>
    </footer>
</a>
</template>

<script>
import Organization from 'models/organization';
import placeholders from 'helpers/placeholders';
import config from 'config';

export default {
    props: {
        organization: {
            type: Object,
            default: () => new Organization(),
        },
        orgid: null,
        clickable: {
            type: Boolean,
            default: false
        },
        selected: {
            type: Boolean,
            default: false
        }
    },
    computed: {
        logo() {
            if (!this.organization || !this.organization.logo_thumbnail && !this.organization.logo) {
                return placeholders.organization;
            }
            return this.organization.logo_thumbnail || this.organization.logo;
        },
        certified_stamp() {
            return `${config.theme_static}img/certified-stamp.png`;
        }
    },
    created() {
        if (this.orgid) {
            this.organization.fetch(this.orgid);
        }
    },
    methods: {
        click() {
            if (this.clickable) {
                this.$dispatch('organization:clicked', this.organization);
            }
        }
    }
};
</script>
