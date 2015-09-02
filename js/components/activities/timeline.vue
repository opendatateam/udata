<template>
<div>
    <ul class="timeline">
        <li v-repeat="activities">
            <div class="timeline-item">
                <div class="timeline-header">
                    <h5>
                        {{$key}} : {{$value}}
                    </h5>
                </div>
            </div>
        </li>
    </ul>
</div>
</template>

<script>
import activities from 'models/activities';

export default {
    props: ['activities'],
    data: function() {
        return {
            activities: []
        };
    },
    ready: function() {
        this.activities = activities;
    },
    el: '#activities'
};
</script>
