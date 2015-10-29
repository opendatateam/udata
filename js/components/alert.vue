<style lang="less"></style>

<template>
    <div class="alert alert-{{type}}"
        :class="{ 'alert-dismissable': closable }">
        <button type="button" class="close" data-dismiss="alert" aria-hidden="true">×</button>
        <h4>
            <span class="icon fa fa-{{icon}}"></span>
            {{title}}
        </h4>
        {{details}}
    </div>
</template>

<script>
'use strict';

module.exports = {
    name: 'alert-box',
    replace: true,
    data: function() {
        return {
            type: 'success',
            closable: true,
            icon: 'check'
        };
    }
};
</script>
