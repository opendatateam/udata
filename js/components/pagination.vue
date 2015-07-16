<template>
    <ul class="pagination pagination-sm no-margin" v-show="p && p.pages > 1">
        <li v-class="disabled: !p || p.page == 1">
            <a title="{{ 'First page'|i18n }}" class="pointer"
                v-on="click: p.go_to_page(1)">
                &laquo;
            </a>
        </li>
        <li v-class="disabled: !p || p.page == 1">
            <a title="{{'Previous page'|i18n}}" class="pointer"
                v-on="click: p.previousPage()">
                &lsaquo;
            </a>
        </li>
        <li v-repeat="current:range" v-class="active: current == p.page">
            <a v-on="click: p.go_to_page(current)" class="pointer">{{ current }}</a>
        </li>
        <li v-class="disabled: !p || p.page == p.pages">
            <a title="{{'Next page'|i18n}}" class="pointer"
                v-on="click: p.nextPage()">
                &rsaquo;
            </a>
        </li>
        <li v-class="disabled: !p || p.page == p.pages">
            <a title="{{'Last page'|i18n}}" class="pointer"
                v-on="click: p.go_to_page(p.pages)">
                &raquo;
            </a>
        </li>
    </ul>
</template>

<script>
'use strict';

var nb = 2;
module.exports = {
    name: 'pagination-widget',
    replace: true,
    data: function() {
        return {
            p: {}
        }
    },
    props: ['p'],
    computed: {
        start: function() {
            if (!this.p) {
                return -1;
            }
            return this.p.page <= nb ? 1 : this.p.page - nb;
        },
        end: function() {
            if (!this.p) {
                return -1;
            }
            return this.p.page + nb > this.p.pages ? this.p.pages : this.p.page + nb;
        },
        range: function() {
            if (isNaN(this.start) || isNaN(this.end) || this.start >= this.end) return [];
            return Array
                .apply(0, Array(this.end + 1 - this.start))
                .map(function (element, index) {
                    return index + this.start;
                }.bind(this));
        }
    }
};
</script>
