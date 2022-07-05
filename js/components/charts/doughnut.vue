<template>
    <div class="chart" :style="{height: height}" v-el:container>
        <canvas v-el:canvas height="100%"></canvas>
    </div>
</template>

<script>
import Chart from 'chart.js';
import config from 'config';

export default {
    name: 'chartjs-doughnut',
    props: ['score'],
    ready() {
        this.build_chart()
    },
    methods: {
        build_chart() {
            if (!this.score) return;

            const data = {
                datasets: [{
                    backgroundColor: [ "#3C8DBC", "#F5F5F5" ],
                    data: [ this.score, 1 - this.score ],
                }],
            };

            const ctx = this.$els.canvas.getContext('2d');

            new Chart(ctx, {
                type: 'doughnut',
                data: data,
                options: {
                    tooltips: {
                        enabled: false
                    },
                    hover: {
                        mode: null
                    }
                }
            });
        },
    },
    watch: {
        score() {
            this.build_chart();
        }
    }
};
</script>
