<template>
<vform v-ref:form :fields="fields" :model="dataset"></vform>
</template>

<script>
export default {
    props: ['dataset'],
    data: function() {
        return {
            fields: ['title', 'description']
            // fields: [{
            //         id: 'title',
            //         label: this._('Title')
            //     }, {
            //         id: 'description',
            //         type: 'markdown',
            //         label: this._('Description'),
            //     }]
        };
    },
    components: {
        vform: require('components/form/vertical-form.vue')
    }
};
</script>
