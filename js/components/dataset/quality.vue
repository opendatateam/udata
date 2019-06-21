<template>
<div>
<box :title="title" icon="thumbs-up" boxclass="box-solid" v-if="quality">
    <doughnut :score="quality.score + 1" width="200px" height="200px"></doughnut>
    <h4>{{ _('The aim of that box is to help you improve the quality of the (meta)data associated to your dataset.') }}</h4>
    <p>{{ _('It gives you an overview of what will be useful for contributors to find and reuse your data.') }}</p>

    <qa-section :title="_('Description')"
        :condition="quality.description_length > 300"
        :ok="_('That is great!')"
        :ko="_('Why not improve it?')">
        <p>{{ _('Try to be as descriptive as you can for your resources (how you use it yourself, which edge cases you solved, what data is missing and so on).') }}</p>
        <p>{{ _('Your description has currently {description_length} caracters.', {description_length: quality.description_length}) }}</p>
    </qa-section>

    <qa-section :title="_('Tags')"
        :condition="quality.tags_count > 3"
        :ok="_('That is great!')"
        :ko="_('Why not add some more?')">
        <p>{{ _('Tags helps your reusers to find your resources, that is very important to make your dataset popular.') }} </p>
    </qa-section>

    <qa-section :title="_('Open formats')"
        :condition="!quality.has_only_closed_or_no_formats"
        :ok="_('You currently have some open formats!')"
        :ko="_('You only have closed formats or no format defined. Can you fill the format info or export some resources in an open format?')">
        <p>{{ _('The open data community enjoy using files in open formats that can be manipulated easily through open software and tools. Make sure you publish your data at least in formats different from XLS, DOC and PDF.') }}</p>
    </qa-section>

    <qa-section :title="_('Discussions')"
        :condition="quality.discussions && !quality.has_untreated_discussions"
        :ok="_('You are currently involved in all discussions!')"
        :ko="_('You have some untreated discussion threads. Why do not you give it a look below?')"
        :info="_('No discussion yet? Try to involve users via social networks and/or by email.')"
        :show-info="!quality.discussions">
        <p>{{ _('Discussing with the community about your datasets is key to involve developers and hackers in your open process. The feedback from reusers of your data is unvaluable and should be answered rather quickly.') }}</p>
    </qa-section>

    <qa-section :title="_('Up-to-date')"
        :condition="(quality.frequency && quality.update_in <= 0) || !quality.frequency"
        :ok="_('That is great!')"
        :ko="_('Need an update since {days} days.', {days: quality.update_in || '0'})">
        <p>{{ _('Proposing up-to-date and incremental data makes it possible for reusers to establish datavisualisations on the long term.') }}</p>
        <p v-if="quality.frequency">{{ _('You currently set your frequency to {frequency}.', {frequency: quality.frequency}) }}</p>
        <p v-if="!quality.frequency">{{ _('You currently have no frequency set for that dataset, is that pertinent?') }}</p>
    </qa-section>

    <qa-section :title="_('Availability')" v-if="quality.has_resources"
        :condition="!quality.has_unavailable_resources"
        :ok="_('All your resources looks to be directly available. That is great!')"
        :ko="_('Some of your resources may have broken links or temporary unavailability. Try to fix it as fast as you can (see the list below).')">
        <p>{{ _('The availability of your distant resources (if any) is crucial for reusers. They trust you for the reliability of these data both in terms of reachability and ease of access.') }}</p>
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
