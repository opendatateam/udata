<style lang="less">
.box {
    .box-tools {
        > * {
            float: right;
        }

        .text-muted {
            color: #777 !important;
        }

        .box-search {
            // float: right;
            width: 180px;
            display: inline-block;

            input:focus {
                -webkit-box-shadow: none;
                -moz-box-shadow: none;
                box-shadow: none;
                border-color: transparent!important;
            }

            input[type="text"], .btn {
                box-shadow: none;
                background-color: #fbfbfb;
                border: 1px solid #fbfbfb;

                &:focus {
                    background-color: #fff;
                    color: #666;

                    & + .input-group-btn .btn {
                        background-color: #fff;
                        border-left-color: #fff;
                        color: #666;
                    }
                }
            }

            > * {
                border-top: 1px solid #eee;
                border-bottom: 1px solid #eee;
                &:first-child {
                    border-left: 1px solid #eee;
                }

                &:last-child {
                    border-right: 1px solid #eee;
                }
            }
        }

        .btn-box-tool {
            font-size: 14px;
            padding: 6px 8px;
        }

        .btn-group {
            vertical-align: inherit;
        }
    }

    form {
        margin: 10px;
    }
}

</style>
<template>
    <div class="box {{ boxclass }}">
        <header class="box-header" v-show="title || icon">
            <i v-show="icon" class="fa fa-{{icon}}"></i>
            <h3 class="box-title">{{title}}</h3>
            <div class="box-tools">
                <slot name="tools"></slot>
            </div>
        </header>
        <div class="box-body {{bodyclass}}">
            <slot></slot>
        </div>
        <div class="overlay" v-show="loading">
            <span class="fa fa-refresh fa-spin"></span>
        </div>
        <div class="box-footer clearfix {{footerclass}}" v-show="footer">
            <slot name="footer"></slot>
        </div>
    </div>
</template>

<script>
export default {
    name: 'box-container',
    replace: true,
    props: {
        title: String,
        icon: null,
        boxclass: {
            type: String,
            default: ''
        },
        bodyclass: {
            type: String,
            default: ''
        },
        footerclass: {
            type: String,
            default: ''
        },
        loading: Boolean,
        footer: null
    }
};
</script>
