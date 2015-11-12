<template>
    <div class="alert alert-{{alert.type || 'success'}}"
        :class="{ 'alert-dismissable': closable }">
        <button type="button" class="close" data-dismiss="alert" aria-hidden="true">×</button>
        <h4>
            <span class="icon fa fa-{{alert.icon || 'check'}}"></span>
            {{alert.title}}
        </h4>
        {{alert.details}}
    </div>
</template>

<script>
export default {
    name: 'alert-box',
    replace: true,
    props: {
        alert: Object
    },
    computed: {
        closable() {
            return this.alert.closable === undefined ? true : this.alert.closable;
        }
    }
};
</script>
