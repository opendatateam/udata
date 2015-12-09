<template>
<box :title="title" icon="thumbs-up" boxclass="box-solid" v-if="quality">
    <doughnut :score="quality.score + 1"></doughnut>
    <h4>{{ _('The aim of that box is to help you improve the quality of the (meta)data associated to your dataset.') }}</h4>
    <p>{{ _('It gives you an overview of what will be useful for contributors to find and reuse your data.') }}</p>

    <h3>{{ _('Description') }}</h3>
    <p>{{ _('Try to be as descriptive as you can for your resources (how you use it yourself, which edge cases you solved, what data is missing and so on).') }}</p>
    <p>{{ _('Your description has currently {description_length} caracters.', {description_length: quality.description_length}) }}</p>
    <p v-if="quality.description_length > 300" class="text-success">
        <span class="fa fa-check-circle"></span>
        <strong>{{ _('That is great!') }}</strong>
    </p>
    <p v-if="quality.description_length <= 300" class="text-warning">
        <span class="fa fa-exclamation-circle"></span>
        <strong>{{ _('Why not improve it?') }}</strong>
    </p>

    <h3>{{ _('Tags') }}</h3>
    <p>{{ _('Tags helps your reusers to find your resources, that is very important to make your dataset popular.') }}</p>
    <p v-if="quality.tags_count">{{ _('You currently set {tags_count} tags for that dataset.', {tags_count: quality.tags_count}) }}</p>
    <p v-if="!quality.tags_count" class="text-warning">
        <span class="fa fa-exclamation-circle"></span>
        <strong>{{ _('You currently set no tags for that dataset! Why not add some more?') }}</strong>
    </p>
    <p v-if="quality.tags_count > 3" class="text-success">
        <span class="fa fa-check-circle"></span>
        <strong>{{ _('That is great!') }}</strong>
    </p>
    <p v-if="quality.tags_count <= 3" class="text-warning">
        <span class="fa fa-exclamation-circle"></span>
        <strong>{{ _('Why not add some more?') }}</strong>
    </p>

    <h3>{{ _('Open formats') }}</h3>
    <p>{{ _('The open data community enjoy using files in open formats that can be manipulated easily through open software and tools. Make sure you publish your data at least in formats different from XLS, DOC and PDF.') }}</p>
    <p v-if="!quality.has_only_closed_formats" class="text-success">
        <span class="fa fa-check-circle"></span>
        <strong>{{ _('You currently have other formats!') }}</strong>
    </p>
    <p v-if="quality.has_only_closed_formats" class="text-warning">
        <span class="fa fa-exclamation-circle"></span>
        <strong>{{ _('You only have closed formats. Cannot you export some in open ones?') }}</strong>
        </p>

    <h3>{{ _('Discussions') }}</h3>
    <p>{{ _('Discussing with the community about your datasets is key to involve developers and hackers in your open process. The feedback from reusers of your data is unvaluable and should be answered rather quickly.') }}</p>
    <p v-if="quality.discussions && !quality.has_untreated_discussions" class="text-success">
        <span class="fa fa-check-circle"></span>
        <strong>{{ _('You are currently involved in all discussions!') }}</strong>
    </p>
    <p v-if="quality.discussions && quality.has_untreated_discussions" class="text-warning">
        <span class="fa fa-exclamation-circle"></span>
        <strong>{{ _('You have some untreated discussion threads. Why do not you give it a look below?') }}</strong>
    </p>
    <p v-if="!quality.discussions" class="text-info">
        <span class="fa fa-question-circle"></span>
        <strong>{{ _('No discussion yet? Try to involve users via social networks and/or by email.') }}</strong>
    </p>

    <h3>{{ _('Up-to-date') }}</h3>
    <p>{{ _('Proposing up-to-date and incremental data makes it possible for reusers to establish datavisualisations on the long term.') }}</p>
    <p v-if="quality.frequency">{{ _('You currently set your frequency to {frequency}.', {frequency: quality.frequency}) }}</p>
    <p v-if="!quality.frequency">{{ _('You currently have no frequency set for that dataset, is that pertinent?') }}</p>
    <p v-if="quality.update_in <= 0" class="text-success">
        <span class="fa fa-check-circle"></span>
        <strong>{{ _('That is great!') }}</strong>
    </p>
    <p v-if="quality.update_in > 0" class="text-warning">
        <span class="fa fa-exclamation-circle"></span>
        <strong> {{ _('Need an update since {days} days.', {days:quality.update_in}) }}</strong>
    </p>

    <div v-if="quality.has_resources">
        <h3>{{ _('Availability') }}</h3>
        <p>{{ _('The availability of your distant resources (if any) is crucial for reusers. They trust you for the reliability of these data both in terms of reachability and ease of access.') }}</p>
        <p v-if="!quality.has_unavailable_resources" class="text-success">
            <span class="fa fa-check-circle"></span>
            <strong>{{ _('All your resources looks to be directly available. That is great!') }}</strong>
        </p>
        <p v-if="quality.has_unavailable_resources" class="text-warning">
            <span class="fa fa-exclamation-circle"></span>
            <strong>{{ _('Some of your resources may have broken links or temporary unavailability. Try to fix it as fast as you can (see the list below).') }}</strong>
        </p>
    </div>
</box>
</template>

<script>
export default {
    name: 'dataset-quality',
    props: ['quality'],
    data: function() {
        return {
            title: this._('Quality')
        };
    },
    components: {
        box: require('components/containers/box.vue'),
        doughnut: require('components/charts/doughnut.vue')
    }
};
</script>
