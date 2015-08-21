<style lang="less">

</style>

<template>
<input type="hidden" v-attr="
    id: field.id,
    name: field.id,
    required: required,
    value: value"></input>
</template>

<script>
export default {
    name: 'hidden-input',
    inherit: true,
    replace: true
};
</script>
