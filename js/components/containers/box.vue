<style lang="less">
.box-tools {
    > * {
        float: right;
    }

    .text-muted {
        color: #777 !important;
    }

    .box-search {
        // float: right;
        width: 180px;
        display: inline-block;

        input:focus {
            -webkit-box-shadow: none;
            -moz-box-shadow: none;
            box-shadow: none;
            border-color: transparent!important;
        }

        input[type="text"], .btn {
            box-shadow: none;
            background-color: #fbfbfb;
            border: 1px solid #fbfbfb;

            &:focus {
                background-color: #fff;
                color: #666;

                & + .input-group-btn .btn {
                    background-color: #fff;
                    border-left-color: #fff;
                    color: #666;
                }
            }
        }

        > * {
            border-top: 1px solid #eee;
            border-bottom: 1px solid #eee;
            &:first-child {
                border-left: 1px solid #eee;
            }

            &:last-child {
                border-right: 1px solid #eee;
            }
        }
    }
}

</style>
<template>
    <div class="box {{ boxclass }}">
        <header class="box-header" v-show="title || icon">
            <i v-show="icon" class="fa fa-{{icon}}"></i>
            <h3 class="box-title">{{title}}</h3>
            <div class="box-tools">
                <content v-ref="tools" select="aside"></content>
            </div>
        </header>
        <div class="box-body {{bodyclass || ''}}">
            <content></content>
        </div>
        <div class="overlay" v-show="loading">
            <span class="fa fa-refresh fa-spin"></span>
        </div>
        <div class="box-footer clearfix {{footerclass || ''}}" v-show="has_footer">
            <content select="box-footer"></content>
        </div>
    </div>
</template>

<script>
'use strict';

var $ = require('jquery');

module.exports = {
    name: 'box-container',
    replace: true,
    // inherit: true,
    computed: {
        has_header: function() {
            return $(this.$el).find('.box-header > *').length > 0;
        },
        has_footer: function() {
            return $(this.$el).find('.box-footer > *').length > 0;
        }
    },
    props: ['title', 'icon', 'boxclass', 'bodyclass', 'footerclass', 'loading']
};
</script>
