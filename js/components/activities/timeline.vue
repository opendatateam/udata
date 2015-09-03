<template>
<ul class="timeline">
    <li v-repeat="activity in activities.data">
        <div class="timeline-item">
            <div class="timeline-header">
                <h5>
                    {{activity.actoer.first_name}} {{activity.actoer.last_name}}
                </h5>
            </div>
        </div>
    </li>
</ul>
</template>

<script>
import SiteActivityPage from 'models/activities';

export default {
    el: '#activities',
    data: function() {
        return {
            activities: new SiteActivityPage().fetch()
        };
    }
};
</script>
