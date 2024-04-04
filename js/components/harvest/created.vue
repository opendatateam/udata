<template>
<div>
<div class="page-header">
    <h1>{{ _('Your harvester has been created') }}</h1>
</div>
<div class="row">
    <div class="col-xs-12 lead text-center">
        <p>{{ _('Your harvester is now pending for team review.') }}</p>
        <div v-if="harvestValidationContactForm">
            <p>{{ _('Please inform us through the following contact form if you want us to validate your harvester:') }}</p>
            <p>
                <a href="{{ harvestValidationContactForm }}">
                    {{ _('Harvester validation contact form') }}
                </a>
            </p>
        </div>
        <p>{{ _("You'll be notified on approval (or refusal)") }}</p>
    </div>
</div>

<div class="row">
    <div class="col-xs-12 text-center">
        <button class="btn btn-primary btn-flat"
            v-link="{name: 'harvester', params: {oid: source.id}}">
            {{ _('See in the administration') }}
        </button>
    </div>
</div>
</div>
</template>

<script>
import config from 'config';

export default {
    props: {
        source: {type: Object, default: () => {}}
    },
    data() {
        return {
            harvestValidationContactForm: config.harvest_validation_contact_form
        }
    }
};
</script>
