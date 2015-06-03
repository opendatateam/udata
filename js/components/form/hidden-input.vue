<style lang="less">

</style>

<template>
<input type="hidden" v-attr="
    id: field.id,
    name: field.id,
    required: required,
    value: value.id"></input>
</template>

<script>
'use strict';

module.exports = {
    name: 'hidden-input',
    inherit: true,
    replace: true
};
</script>
