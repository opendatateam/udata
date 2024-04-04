<template>
<div>
<box :title="title" icon="thumbs-up" boxclass="box-solid" v-if="quality">
    <doughnut :score="quality.score" width="200px" height="200px"></doughnut>
    <h4>{{ _('The aim of that box is to help you improve the quality of the (meta)data associated to your dataset.') }}</h4>
    <p>{{ _('It gives you an overview of what will be useful for contributors to find and reuse your data.') }}</p>

    <qa-section :title="_('Description')"
        :condition="quality.dataset_description_quality"
        :ok="_('That is great!')"
        :ko="_('Why not improve it?')">
        <p>{{ _('Try to be as descriptive as you can for your resources (how you use it yourself, which edge cases you solved, what data is missing and so on).') }}</p>
    </qa-section>

    <qa-section :title="_('Open formats')"
        :condition="quality.has_open_format"
        :ok="_('You currently have some open formats!')"
        :ko="_('You only have closed formats or no format defined. Can you fill the format info or export some resources in an open format?')">
        <p>{{ _('The open data community enjoy using files in open formats that can be manipulated easily through open software and tools. Make sure you publish your data at least in formats different from XLS, DOC and PDF.') }}</p>
    </qa-section>

    <qa-section :title="_('Frequency')"
        :condition="quality.update_frequency"
        :ok="_('That is great!')"
        :ko="_('You currently have no frequency set for that dataset, is that pertinent?')">
    </qa-section>

    <qa-section :title="_('Up-to-date')"
        :condition="quality.update_frequency && quality.update_fulfilled_in_time"
        :ok="_('That is great!')"
        :ko="_('The data does not seem to be up-to-date according to the chosen update frequency.')">
        <p>{{ _('Proposing up-to-date and incremental data makes it possible for reusers to establish datavisualisations on the long term.') }}</p>
    </qa-section>

    <qa-section :title="_('Availability')" v-if="quality.has_resources"
        :condition="quality.all_resources_available"
        :ok="_('All your resources seem to be directly available. That is great!')"
        :ko="_('Some of your resources may have broken links or temporary unavailability. Try to fix it as fast as you can (see the list below).')">
        <p>{{ _('The availability of your distant resources (if any) is crucial for reusers. They trust you for the reliability of these data both in terms of reachability and ease of access.') }}</p>
    </qa-section>

    <qa-section :title="_('Documentation')" v-if="quality.has_resources"
        :condition="quality.resources_documentation"
        :ok="_('Your resources seem to be documented. That is great!')"
        :ko="_('Some of your resources do not have a description. Try to fix by providing one for each resource or by uploading a documentation resource.')">
        <p>{{ _('The documentation of your resources is crucial for reusers.') }}</p>
    </qa-section>

    <qa-section :title="_('License')"
        :condition="quality.license"
        :ok="_('That is great!')"
        :ko="_('You currently have no license set for that dataset, is that pertinent?')">
    </qa-section>

    <qa-section :title="_('Temporal coverage')"
        :condition="quality.temporal_coverage"
        :ok="_('That is great!')"
        :ko="_('You currently have no temporal coverage set for that dataset, is that pertinent?')">
    </qa-section>

    <qa-section :title="_('Spatial coverage')"
        :condition="quality.spatial"
        :ok="_('That is great!')"
        :ko="_('You currently have no spatial coverage set for that dataset, is that pertinent?')">
    </qa-section>
</box>
</div>
</template>

<script>
import Box from 'components/containers/box.vue';
import Doughnut from 'components/charts/doughnut.vue';
import QaSection from './quality-section.vue';

export default {
    name: 'dataset-quality',
    components: {Box, Doughnut, QaSection},
    props: ['quality'],
    data() {
        return {
            title: this._('Quality')
        };
    },
};
</script>
