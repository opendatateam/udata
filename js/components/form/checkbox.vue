<style lang="less">
.checkbox label {
    font-weight: bold;
}
</style>

<template>
<div class="checkbox">
    <label for="{{field.id}}" v-class="required: required">
        <input type="checkbox" v-attr="
            id: field.id,
            name: field.id,
            checked: value"></input>
        {{ field.label }}
    </label>
</div>
</template>

<script>
export default {
    name: 'Checkbox',
    inherit: true,
    replace: true
};
</script>
