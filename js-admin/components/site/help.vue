<template>
<div>
    <div class="nav-tabs-custom">
        <ul class="nav nav-tabs">
            <li class="header">
                <i class="fa fa-help"></i>
                <span v-i18n="Help"></span>
            </li>
            <li class="active">
                <a href="#datasets" data-toggle="tab" v-i18n="Datasets"></a>
            </li>
            <li>
                <a href="#reuses" data-toggle="tab" v-i18n="Reuses"></a>
            </li>
            <!--li class="pull-right">
                <a href="#" class="text-muted">
                    <i class="fa fa-gear"></i>
                </a>
            </li-->
        </ul>
        <div class="tab-content">
            <div class="tab-pane active" id="datasets">
                <b>How to use:</b>
                <p>Exactly like the original bootstrap tabs except you should use
                    the custom wrapper <code>.nav-tabs-custom</code> to achieve this style.</p>
                A wonderful serenity has taken possession of my entire soul,
                like these sweet mornings of spring which I enjoy with my whole heart.
                I am alone, and feel the charm of existence in this spot,
                which was created for the bliss of souls like mine. I am so happy,
                my dear friend, so absorbed in the exquisite sense of mere tranquil existence,
                that I neglect my talents. I should be incapable of drawing a single stroke
                at the present moment; and yet I feel that I never was a greater artist than now.
            </div><!-- /.tab-pane -->
            <div class="tab-pane" id="reuses">
                The European languages are members of the same family. Their separate existence is a myth.
                For science, music, sport, etc, Europe uses the same vocabulary. The languages only differ
                in their grammar, their pronunciation and their most common words. Everyone realizes why a
                new common language would be desirable: one could refuse to pay expensive translators. To
                achieve this, it would be necessary to have uniform grammar, pronunciation and more common
                words. If several languages coalesce, the grammar of the resulting language is more simple
                and regular than that of the individual languages.
            </div><!-- /.tab-pane -->
        </div>
    </div>
</div>
</template>

<script>
'use strict';

module.exports = {
    name: 'homepage-widget',
    replace: true,
    data: function() {
        return {
            current_tab: 'datasets',
            footer: true
        };
    }
};
</script>
