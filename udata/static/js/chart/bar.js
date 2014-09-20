define(['jquery', 'd3', 'chart/base'], function($, d3, BaseChart) {

    return BaseChart.extend({
        draw: function(data) {
            var self = this,
                svg = this.svg,
                bbox = this.bbox();

            var margin = bbox.width / (data.length * 4),
                barWidth = (bbox.width - data.length * margin)  / data.length,
                barHeight = bbox.height,
                borderRadius = barWidth / 5;

            var yMin = d3.min(data, function(d) {
                    return +d.value;
                }),
                yMax = d3.max(data, function(d) {
                    return +d.value;
                }),
                yMargin = Math.max((yMax - yMin) / 10, 1);

            var x = d3.scale.linear()
                    .domain([0, data.length]).range([0, bbox.width]),
                y = d3.scale.linear()
                    .domain([Math.max(yMin - yMargin, -1), Math.max(yMax + yMargin, 10)])
                    .range([bbox.height, 0]),
                opacity = d3.scale.linear().domain([yMin, yMax]).range([0.5, 1]),
                fillOpacity = function(d) { return opacity(d.value); };

            function set_selected(idx) {
                var d = data[idx],
                    difference = parseInt(d.value) - parseInt(data[idx - 1].value),
                    bar = svg.select('.bar[data-index="'+ idx +'"]');

                svg.selectAll('.bar').classed('selected', false);

                bar.classed('selected', true);

                if (difference > 0) {
                    difference = '+' + difference;
                }

                self._setInfobox(d.value, difference, d.label, {
                    top: function() {
                        return y(d.value) - $(this).outerHeight() - 5;
                    },
                    left: function() {
                        return (x(idx) + margin) - ($(this).width() / 2);
                    }
                });
            }

            var bar = svg.selectAll('g.bar-container').data(data).enter().append("g");

            bar.attr("transform", function(d, i) {
                    return "translate(" + i * (barWidth + margin) + ", 0)";
                })
                .classed('bar-container', true);

            bar.append("svg:rect")
                // .attr('x', function(d, i) {console.log(d, i); return i * (barWidth + margin); })
                .attr('y', function(d) { return y(d.value); })
                .attr('width', barWidth)
                .attr('height', function(d) { return bbox.height - y(d.value); })
                .attr('rx', borderRadius)
                .attr('ry', borderRadius)
                .style('fill-opacity', fillOpacity)
                .attr('class', 'bar')
                .attr('data-index', function(d, i) { return i; })
                .attr('data-month', function(d) { return d.label; })
                .attr('data-value', function(d) { return d.value; })
                .on('mouseover', function() {
                    var idx = parseInt(d3.select(this).attr('data-index'));
                    set_selected(idx);
                });

            bar.append("svg:circle")
                .attr('cx', function(d, i) { return barWidth / 2; })
                .attr('cy', function(d) { return y(d.value) + 10; })
                .attr('r', barWidth / 4)
                .attr('class', 'barCircle')
                .style('fill-opacity', fillOpacity);


            svg.on('mouseleave', function() {
                set_selected(data.length - 1);
            })

            set_selected(data.length - 1);
        }

    });

});

