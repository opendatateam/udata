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
<div>
<modal v-ref:modal class="user-modal" small>
    <div class="user-details" slot="modal-content">
        <img class="img-circle"
            :src="user | avatar_url 100"
            :alt="user.fullname"
            :title="user.fullname"/>
        <div class="user-info-block">
            <button type="button" class="close" @click="$refs.modal.close">
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
                    <a class="text-center pointer" @click="toDashboard"
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
</modal>
</div>
</template>

<script>
import Modal from 'components/modal.vue';
import placeholders from 'helpers/placeholders';

export default {
    name: 'user-modal',
    components: {Modal},
    props: ['user'],
    data() {
        return {
            placeholder: placeholders.user
        };
    },
    methods: {
        close() {
            this.$refs.modal.close();
        },
        toDashboard() {
            this.close();
            this.$go(`/user/${this.user.id}`);
        }
    }
};
</script>
