<template>
<div class="info-box"
    :class="{ 'bg-aqua': downloading, 'bg-gray': !downloading }">
    <span class="info-box-icon">
        <span class="fa fa-cloud-upload"></span>
    </span>
    <div class="info-box-content">
        <span class="info-box-text">{{resource.name}}</span>
        <span class="info-box-number">{{resource.filesize | filesize}}</span>
    </div>
</div>
</template>

<script>
export default {
    data: function() {
        return {};
    }
};
</script>
