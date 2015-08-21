<style lang="less">
// .small-box {
//     .icon {
//         bottom: 10px;
//         font-size: 70px;

//         .fa {
//             line-height: 1;
//             text-transform: none;
//         }
//     }
// }

// @keyframes tansformAnimation {
//     from {
//         font-size: 70px;
//     }
//     to {
//         font-size: 80px;
//     }
// }
// @-webkit-keyframes tansformAnimation {
//     from {
//         font-size: 70px;
//     }
//     to {
//         font-size: 80px;
//     }
// }
</style>
<template>
    <a class="small-box pointer" v-class="bgcolor" v-on="click: click">
        <div class="inner">
            <h3>{{value || 0}}</h3>
            <p>{{label}}</p>
        </div>
        <div class="icon">
            <i class="fa" v-class="faicon"></i>
        </div>
        <div class="small-box-footer">
            <span v-i18n="More infos"></span>
            <i class="fa fa-arrow-circle-right"></i>
        </div>
    </a>
</template>

<script>
'use strict';

module.exports = {
    name: 'small-box',
    data: function() {
        return {
            value: 0,
            label: '',
            color: 'aqua',
            icon: '',
            target: null
        };
    },
    computed:  {
        bgcolor: function() {
            return 'bg-' + this.color;
        },
        faicon: function() {
            return 'fa-' + this.icon;
        }
    },
    methods: {
        click: function() {
            if (this.target) {
                if (this.target[0] === '#') {
                    this.$scrollTo(this.target);
                } else {
                    this.$go(this.target);
                }
            }
            this.$dispatch('small-box:click', this);
        }
    }
};
</script>
