<template>
    <div class="chart" :style="{height: height}" v-el:container>
        <canvas v-el:canvas height="100%"></canvas>
    </div>
</template>

<script>
import Chart from 'chart.js';

export default {
    name: 'chartjs-doughnut',
    props: ['score'],
    watch: {
        'score': function() {
            this.build_chart();
        }
    },
    ready: function() {
        this.build_chart()
    },
    methods: {
        build_chart: function() {
            if (!this.score) {
                return;
            }
            let data = [
                {
                    value: this.score,
                    color:"#3C8DBC",
                },
                {
                    value: 10 - this.score,
                    color: "#F5F5F5",
                }
            ];
            let ctx = this.$els.canvas.getContext('2d');
            new Chart(ctx).Doughnut(data, {
                segmentShowStroke : false,
                showTooltips: false,
            });
        },
    }
};
</script>
