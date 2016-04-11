<template>
    <ul class="pagination pagination-sm no-margin" v-show="p && p.pages > 1">
        <li :class="{ 'disabled': !p || p.page == 1 }">
            <a :title="_('First page')" class="pointer"
                @click="p.go_to_page(1)">
                &laquo;
            </a>
        </li>
        <li :class="{ 'disabled': !p || p.page == 1 }">
            <a :title="_('Previous page')" class="pointer"
                @click="p.previousPage()">
                &lsaquo;
            </a>
        </li>
        <li v-for="current in range" :class="{ 'active': current == p.page }">
            <a @click="p.go_to_page(current)" class="pointer">{{ current }}</a>
        </li>
        <li :class="{ 'disabled': !p || p.page == p.pages }">
            <a :title="_('Next page')" class="pointer"
                @click="p.nextPage()">
                &rsaquo;
            </a>
        </li>
        <li :class="{ 'disabled': !p || p.page == p.pages }">
            <a :title="_('Last page')" class="pointer"
                @click="p.go_to_page(p.pages)">
                &raquo;
            </a>
        </li>
    </ul>
</template>

<script>
const nb = 2;

export default {
    name: 'pagination-widget',
    replace: true,
    props: {
        p: Object
    },
    computed: {
        start() {
            if (!this.p) {
                return -1;
            }
            return this.p.page <= nb ? 1 : this.p.page - nb;
        },
        end() {
            if (!this.p) {
                return -1;
            }
            return this.p.page + nb > this.p.pages ? this.p.pages : this.p.page + nb;
        },
        range() {
            if (isNaN(this.start) || isNaN(this.end) || this.start >= this.end) return [];
            return Array
                .apply(0, Array(this.end + 1 - this.start))
                .map((element, index) => {
                    return index + this.start;
                });
        }
    }
};
</script>
