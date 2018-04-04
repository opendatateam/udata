<template>
    <div>
        <div>{{{ message.content | markdown }}}</div>
        
        <div>
            <avatar :user="message.posted_by" :size="18"></avatar>
            {{ message.posted_by.first_name }} {{ message.posted_by.last_name }}
            {{ formatDate(message.posted_on) }} 
            <a href="#{{ discussion }}-{{ index }}"><span class="fa fa-link"></span></a>
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
