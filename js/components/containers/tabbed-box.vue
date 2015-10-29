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
        <header class="box-header">
            <i v-if="icon" class="fa fa-{{icon}}"></i>
            <h3 class="box-title">{{title}}</h3>
            <div class="box-tools">
                <content v-ref:tools select="aside > *"></content>
            </div>
        </header>
        <div class="box-body {{bodyclass || ''}}">
            <content></content>
        </div>
        <div class="box-footer {{footerclass || ''}}" v-if="footer">
            <content v-ref:footer select="footer > *"></content>
        </div>
    </div>
</template>

<script>
'use strict';

var $ = require('jquery');

module.exports = {
    name: 'tabbed-box-container',
    replace: true,
    data: function() {
        return {
            footer: true
        };
    },
    props: ['title', 'icon', 'boxclass', 'bodyclass', 'footerclass'],
    attached: function() {
        this.footer = $(this.$el).find('.box-body > footer').length > 0;
    }
};
</script>
