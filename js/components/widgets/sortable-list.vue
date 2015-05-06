<style lang="less">
.sortable-list {
        margin: 0;
        padding: 0px 0px;
        list-style: none;
        // sortable list element
        > li {
            .border-radius(2px);
            padding: 10px;
            background: @table-striped-color;
            margin-bottom: 2px;
            border-left: 2px solid #e6e7e8;
            color: #444;
            &:last-of-type {
                margin-bottom: 0;
            }
            // Color varaity
            &.danger {
                border-left-color: @red;
            }
            &.warning {
                border-left-color: @yellow;
            }
            &.info {
                border-left-color: @aqua;
            }
            &.success {
                border-left-color: @green;
            }
            &.primary {
                border-left-color: @light-blue;
            }

            > input[type='checkbox']  {
                margin: 0 10px 0 5px;
            }

            .text {
                display: inline-block;
                margin-left: 5px;
                font-weight: 600;
            }

            // Time labels
            .label {
                margin-left: 10px;
                font-size: 9px;
            }

            // Tools and options box
            .tools {
                display: none;
                float: right;
                color: @red;
                // icons
                > .fa, > .glyphicon, > .ion {
                    margin-right: 5px;
                    cursor: pointer;
                }

            }
            &:hover .tools {
                display: inline-block;
            }

            &.done {
                color: #999;
                .text {
                    text-decoration: line-through;
                    font-weight: 500;
                }

                .label {
                    background: @gray!important;
                }
            }
        }

        .handle {
            display: inline-block;
            cursor: move;
            margin: 0 5px;
        }

    }
</style>
<template>
    <ul class="sortable-list">
        <li v-repeat="items">
            <!-- drag handle -->
            <span class="handle">
                <i class="fa fa-ellipsis-v"></i>
                <i class="fa fa-ellipsis-v"></i>
            </span>
            <content></content>
            <!-- General tools such as edit or delete-->
            <div class="tools">
                <content v-ref="tools" select="aside > *"></content>
            </div>
        </li>
        <li>
            <span class="handle">
                <i class="fa fa-ellipsis-v"></i>
                <i class="fa fa-ellipsis-v"></i>
            </span>
            <input type="checkbox" value="" name=""/>
            <span class="text">Make the theme responsive</span>
            <small class="label label-info"><i class="fa fa-clock-o"></i> 4 hours</small>
            <div class="tools">
                <i class="fa fa-edit"></i>
                <i class="fa fa-trash-o"></i>
            </div>
        </li>
        <li>
            <span class="handle">
                <i class="fa fa-ellipsis-v"></i>
                <i class="fa fa-ellipsis-v"></i>
            </span>
            <input type="checkbox" value="" name=""/>
            <span class="text">Let theme shine like a star</span>
            <small class="label label-warning"><i class="fa fa-clock-o"></i> 1 day</small>
            <div class="tools">
                <i class="fa fa-edit"></i>
                <i class="fa fa-trash-o"></i>
            </div>
        </li>
        <li>
            <span class="handle">
                <i class="fa fa-ellipsis-v"></i>
                <i class="fa fa-ellipsis-v"></i>
            </span>
            <input type="checkbox" value="" name=""/>
            <span class="text">Let theme shine like a star</span>
            <small class="label label-success"><i class="fa fa-clock-o"></i> 3 days</small>
            <div class="tools">
                <i class="fa fa-edit"></i>
                <i class="fa fa-trash-o"></i>
            </div>
        </li>
        <li>
            <span class="handle">
                <i class="fa fa-ellipsis-v"></i>
                <i class="fa fa-ellipsis-v"></i>
            </span>
            <input type="checkbox" value="" name=""/>
            <span class="text">Check your messages and notifications</span>
            <small class="label label-primary"><i class="fa fa-clock-o"></i> 1 week</small>
            <div class="tools">
                <i class="fa fa-edit"></i>
                <i class="fa fa-trash-o"></i>
            </div>
        </li>
        <li>
            <span class="handle">
                <i class="fa fa-ellipsis-v"></i>
                <i class="fa fa-ellipsis-v"></i>
            </span>
            <input type="checkbox" value="" name=""/>
            <span class="text">Let theme shine like a star</span>
            <small class="label label-default"><i class="fa fa-clock-o"></i> 1 month</small>
            <div class="tools">
                <i class="fa fa-edit"></i>
                <i class="fa fa-trash-o"></i>
            </div>
        </li>
    </ul>
</template>
