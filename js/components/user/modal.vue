<style lang="less">
.user-details {
    position: relative; padding: 0;
    text-align: center;

    img {
        clear: both;
        position: relative;
        z-index: 1;
        width: 100px;
        // margin: auto;
    }

    .user-info-block {
        width: 100%;
        position: absolute;
        top: 55px;
        background: rgb(255, 255, 255);
        z-index: 0;
        padding-top: 35px;

        .close {
            position: absolute;
            right: 10px;
            top: 5px;
        }

        .user-heading {
            width: 100%;
            text-align: center;
            margin: 10px 0 0;
        }

        .user-actions {
            // float: left;
            width: 100%;
            margin: 0;
            padding: 0;
            list-style: none;
            // border-bottom: 1px solid #428BCA;
            // border-top: 1px solid #428BCA;

            li {
                float: left;
                margin: 0;
                padding: 0;
                width: 50%;

                &:not(:last-child) {
                    border-right: 1px solid white;
                }

                @bgcolor: #428BCA;

                a {
                    padding: 10px;
                    width: 100%;
                    height: 100%;
                    float: left;
                    color: white;
                    background: @bgcolor;

                    &:hover {
                        color: #fff;
                        background: lighten(@bgcolor, 10%);
                    }
                }

            }
        }

        .user-body {
            padding: 5%;
            width: 100%;
        }
    }
}
</style>
<template>
<div class="modal fade user-modal" tabindex="-1" role="dialog" aria-hidden="true">
    <div class="modal-dialog modal-sm">
        <div class="user-details">
            <img class="img-circle"
                :src="user.avatar || placeholder"
                :alt="user.fullname"
                :title="user.fullname"/>
            </div-->
            <div class="user-info-block">
                <button type="button" class="close" data-dismiss="modal">
                    <span aria-hidden="true">&times;</span>
                    <span class="sr-only" v-i18n="Close"></span>
                </button>
                <div class="user-heading">
                    <h3>{{user.fullname}}</h3>
                    <span class="help-block">{{{ user.about | markdown }}}</span>
                </div>
                <ul class="user-actions clearfix">
                    <li>
                        <a :href="user.page" class="text-center"
                            :title="_('Profile')">
                            <span class="fa fa-2x fa-user"></span>
                        </a>
                    </li>
                    <li>
                        <a class="text-center pointer" @click="to_dashboard"
                             :title="_('Dashboard')">
                            <span class="fa fa-2x fa-dashboard"></span>
                        </a>
                    </li>
                </ul>
                <div class="user-body" v-show="$options._content">
                    <slot></slot>
                </div>
            </div>
        </div>
    </div>
</div>
</template>

<script>
import Modal from 'mixins/modal';

export default {
    name: 'user-modal',
    replace: true,
    mixins: [Modal],
    props: ['user'],
    data: function() {
        return {
            placeholder: require('helpers/placeholders').user
        };
    },
    methods: {
        to_dashboard: function() {
            this.close();
            this.$go('/user/' + this.user.id);
        }
    }
};
</script>
