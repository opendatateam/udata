<style lang="less">
/* Warning:
    As markdown content is not rendered by Vue.js,
    scoped style doesn't work for styling markdown content
*/

.discussion-message {
    display: flex;
    flex-direction: row;

    padding-top: 1.25em;

    > .avatar {
        margin-right: 1em;
        flex-basis: auto;
    }

    .message-content {
        display: flex;
        flex-direction: column;
        min-width: 0; // Override Flex default to auto
        flex-grow: 1;

        .message-header {
            display: flex;
            flex: 0 0 auto;
            margin-bottom: 0.5em;

            .author {
                flex: 1 0 auto;
                font-weight: bold;
            }

            .posted_on {
                flex: 0 0 auto;
                text-align: right;

                .fa {
                    // Space before anchor
                    margin-left: 5px;
                }
            }
        }

        .body {
            flex: 1 0 auto;

            a, code {
                word-wrap: break-word;
                word-break: break-all;
            }

            pre {
                code {
                    word-wrap: normal;
                    word-break: normal;
                }
            }
        }
    }
}

@media only screen and (max-width: 480px){
    .avatar img {
        width : 32px;
        height: 32px;
    }
}

</style>
<template>
    <div class="discussion-message">
        <div class="avatar">
            <a href="{{ message.posted_by.page }}"><avatar :user="message.posted_by"></avatar></a>
        </div>
        <div class="message-content">
            <div class="message-header">
                <div class="author">
                    <a href="{{ message.posted_by.page }}">{{ message.posted_by | display }}</a>
                </div>

                <div class="posted_on">
                    {{ formatDate(message.posted_on) }}
                    <a href="#{{ discussion }}-{{ index }}"><span class="fa fa-link"></span></a>
                </div>
            </div>

            <div class="body">
                {{{ message.content | markdown }}}
            </div>
       </div>
    </div>
</template>
<script>
import moment from 'moment';
import Avatar from 'components/avatar.vue';

export default {
    components: { Avatar },
    props: {
        message: Object,
        discussion: String,
        index: Number,
    },
    methods: {
        formatDate(val) {
            return moment(val).format('LL');
        }
    }
}

</script>
