<style scoped lang="less">
.message {
    display: flex;
    flex-direction: row;
    
    padding-top: 1.25em;

    & > div {
        display: flex;
        flex-grow: 1;
        flex-flow: row wrap;
        justify-content: space-between;
        flex-basis: 100%;
    }
    
    & > .avatar {
        margin-right: 1em;
        flex-basis: auto;
    }

    div.author {
        font-weight: bold;
        margin-bottom: 0.5em;
    }

    div.posted_on {
        text-align: right;
    }

    div.body {
        overflow-wrap: break-word;
        word-wrap: break-word;
        word-break: break-all;
        flex-basis: 100%;
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
    <div class="message">
        <div class="avatar">
            <a href="{{ message.posted_by.page }}"><avatar :user="message.posted_by"></avatar></a>
        </div>
        <div>
            <div class="author">
                <a href="{{ message.posted_by.page }}">{{ message.posted_by.first_name }} {{ message.posted_by.last_name }}</a>
            </div>
           
            <div class="posted_on">
                {{ formatDate(message.posted_on) }} 
                <a href="#{{ discussion }}-{{ index }}"><span class="fa fa-link"></span></a>
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
