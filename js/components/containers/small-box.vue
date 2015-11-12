<template>
    <a class="small-box pointer" :class="[ bgcolor ]" @click="click">
        <div class="inner">
            <h3>{{value | numbers}}</h3>
            <p>{{label}}</p>
        </div>
        <div class="icon">
            <i class="fa" :class="[ faicon ]"></i>
        </div>
        <div v-if="target" class="small-box-footer">
            <span v-i18n="More infos"></span>
            <i class="fa fa-arrow-circle-right"></i>
        </div>
    </a>
</template>

<script>
export default {
    name: 'small-box',
    props: {
        value: null,  // No type check
        label: String,
        icon: String,
        color: {
            type: String,
            default: 'aqua'
        },
        target: null  // No type check
    },
    computed:  {
        bgcolor: function() {
            return 'bg-' + this.color;
        },
        faicon: function() {
            return 'fa-' + this.icon;
        }
    },
    methods: {
        click: function() {
            if (this.target) {
                if (this.target[0] === '#') {
                    this.$scrollTo(this.target);
                } else {
                    if (this.$go) {
                        this.$go(this.target);
                    } else {
                        window.location = this.target;
                    }
                }
            }
            this.$dispatch('small-box:click', this);
        }
    }
};
</script>
