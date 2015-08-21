<style lang="less">

</style>

<template>
<div class="info-box"
    v-class="bg-aqua: downloading, bg-gray: !downloading">
    <span class="info-box-icon">
        <span class="fa fa-cloud-upload"></span>
    </span>
    <div class="info-box-content">
        <span class="info-box-text">{{resource.name}}</span>
        <span class="info-box-number">{{resource.size | filesize}}</span>
        <!--div class="progress">
            <div class="progress-bar" style="width: {{progress}}%"></div>
        </div>
        <span class="progress-description">
        {{progress}}%
        </span-->
    </div>
</div>
</template>

<script>
'use strict';

module.exports = {
    data: function() {
        return {};
    }
};
</script>
