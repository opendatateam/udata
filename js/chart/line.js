define(['jquery', 'd3', 'chart/base'], function($, d3, BaseChart) {

    return BaseChart.extend({
        draw: function(data) {

            var self = this,
                svg = this.svg,
                bbox = this.bbox(),
                infobox = d3.select(this.$infobox[0]),
                radius = 14;

            var current = data[data.length - 1];

            var yMin = d3.min(data, function(d) {
                    return +d.value;
                }),
                yMax = d3.max(data, function(d) {
                    return +d.value;
                }),
                yMargin = Math.max((yMax - yMin) / 10, 1);

            var x = d3.scale.linear().domain([0, data.length - 1]).range([0, bbox.width - radius]),
                y = d3.scale.linear()
                    .domain([Math.max(yMin - yMargin, 0), Math.max(yMax + yMargin, 10)])
                    .range([bbox.height, 0]);

            var sliceWidth = Math.round((bbox.width - radius) / data.length),
                sliceHeight = bbox.height;

            function set_selected(idx) {
                var row = data[idx];

                svg.selectAll('.blue_circle_background')
                    .classed('selected', false)
                    .each(function(d, i) {
                        if (d3.select(this).attr('data-identifier') == idx) {
                            d3.select(this).classed('selected', true);
                        }
                    });

                svg.selectAll('.lineOnSelect')
                    .classed('selected', false)
                    .each(function(d, i) {
                        if (d3.select(this).attr('data-identifier') == idx) {
                            d3.select(this).classed('selected', true);
                        }
                    });

                difference = parseInt(row.value) - parseInt(data[idx - 1].value);

                if (difference > 0) {
                    difference = '+' + difference;
                }

                self._setInfobox(row.value, difference, row.label, {
                    top: function() {
                        return y(row.value) - $(this).outerHeight() - radius;
                    },
                    left: x(idx) + radius
                });

                svg.style('cursor', 'pointer');
            }

            var line = d3.svg.line()
                .x(function(d, i) {
                    return x(i);
                })
                .y(function(d, i) {
                    var yPos = y(d.value),
                        xPos = x(i);

                    if (i != 0) {
                        svg.append("svg:circle")
                            .attr("cx", xPos)
                            .attr("cy", yPos)
                            .attr("data-identifier", i)
                            .attr("r", radius)
                            .attr("class", "blue_circle_background");

                        svg.append("svg:circle")
                            .attr("cx", xPos)
                            .attr("cy", yPos)
                            .attr("data-identifier", i)
                            .attr("r", 6)
                            .style("filter", "#selected_point")
                            .attr("class", "blue_circle");

                        svg.append("line")
                            .attr("class", "lineOnSelect")
                            .attr("x1", xPos)
                            .attr("y1", yPos + radius)
                            .attr("x2", xPos)
                            .attr("y2", bbox.height)
                            .attr("data-identifier", i);

                        svg.append("line")
                            .attr("class", "lineOnSelect")
                            .attr("x1", xPos)
                            .attr("y1", yPos - radius)
                            .attr("x2", xPos)
                            .attr("y2", 0)
                            .attr("data-identifier", i);

                        // Mouse overlay
                        svg.append("svg:rect")
                            .attr('x', xPos - (sliceWidth / 2))
                            .attr('y', 0)
                            .attr('width', sliceWidth)
                            .attr('height', sliceHeight)
                            .style('fill-opacity', 0)
                            .attr('data-index', i)
                            .on('mousemove', function() {
                                var overlay = d3.select(this),
                                    idx = parseInt(overlay.attr('data-index'));

                                set_selected(idx);
                            });
                    }

                    return yPos;
                });

            var area = d3.svg.area()
                .x(function(d, i) {
                    return x(i);
                })
                .y0(bbox.height)
                .y1(function(d) {
                    return y(d);
                });

            var valuesList = [];

            for (var n in data) {
                valuesList.push(data[n].value);
            }

            svg.append("path")
                .datum(valuesList)
                .attr("class", "area")
                .attr("d", area);

            svg.append("svg:path").attr("d", line(data));

            // svg.on('mouseout', function() {
            //     infobox.classed('selected', false);
            //     svg.style('cursor', 'auto');
            //     svg.selectAll('.blue_circle_background').classed('selected', false);
            //     svg.selectAll('.lineOnSelect').classed('selected', false);
            // });

            svg.on('mouseout', function() {
                set_selected(data.length - 1);
            });

            set_selected(data.length - 1);
        }
    });

});
