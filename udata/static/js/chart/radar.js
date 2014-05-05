define(['jquery', 'd3'], function($, d3) {
    return {
        draw: function(id, d, options) {
            var cfg = {
                radius: 5,
                w: 150,
                h: 150,
                factor: 1,
                factorLegend: .85,
                levels: 3,
                bg_colors: ['#49A5D6', '#69B5DD', "#71BCE2", '#72BCE3'],
                maxValue: 0,
                radians: 2 * Math.PI,
                opacityArea: 0.6,
                ToRight: 5,
                TranslateX: 65,
                TranslateY: 5,
                ExtraWidthX: 100,
                ExtraWidthY: 100,
                color: ["#FFB311", '#72cf70', '#bc7666'],
                infoBox: '.selectedInfos'
            };

            if ('undefined' !== typeof options) {
                for (var i in options) {
                    if ('undefined' !== typeof options[i]) {
                        cfg[i] = options[i];
                    }
                }
            }

            var labelValue = id + ' > p';
            var labelDescription = id + ' > h4';
            var container = id;
            id = id + ' > div';


            d3.select(labelValue).text(d.dataInformation.globalValue);
            d3.select(labelDescription).text(d.dataInformation.label);

            if (!d.dataInformation.globalValue || !d.dataInformation.label || !d.receivedData){
                $(id).append('<div class="no-data">Données non disponibles</div>');
                console.log('ERREUR FICHIER RADAR');
                $(container+' h4').hide();
                $(container+' p').hide();
                $.ajax({
                    type: "GET",
                    url: './php/create_issue.php?issue_title=[BUG RadarChart] Json file not valid or not existing&issue_body=The Json\'s file has not been received. The graph has not been displayed.',
                    dataType: "html",

                    success: function(data) {
                        if (data=='success'){
                            console.log('Error sent to Github');
                        }
                    }
                });

                return false;
            }

            for (var i = 0 ; i<d.receivedData[0].length ; i++){
                if (isNaN(d.receivedData[0][i].value) || d.receivedData[0][i].value<=0){
                    console.log('ERREUR FORMAT RADAR');
                    $(id).append('<div class="no-data">Données non disponibles</div>');
                    $(container+' h4').hide();
                    $(container+' p').hide();

                    $.ajax({
                        type: "GET",
                        url: './php/create_issue.php?issue_title=[BUG RadarChart] Json format not valid&issue_body=The Json\'s datas were not valid.',
                        dataType: "html",

                        success: function(data) {
                            if (data=='success'){
                                console.log('Error sent to Github');
                            }
                        }
                    });

                    return false;
                }
            }

            d = d.receivedData;
            cfg.infoBox = id + ' > ' + cfg.infoBox;

            cfg.maxValue = Math.max(cfg.maxValue, d3.max(d, function(i) {
                return d3.max(i.map(function(o) {
                    return o.value;
                })) + 0.2
            }));

            var allAxis = (d[0].map(function(i, j) {
                return i.axis
            }));
            var total = allAxis.length;
            var radius = cfg.factor * Math.min(cfg.w / 2, cfg.h / 2);
            var Format = d3.format('%');
            d3.select(id).select("svg").remove();

            var g = d3.select(id)
                .append("svg")
                .attr("width", cfg.w + cfg.ExtraWidthX)
                .attr("height", cfg.h + cfg.ExtraWidthY)
                .append("g")
                .attr("transform", "translate(" + cfg.TranslateX + "," + cfg.TranslateY + ")");;

            var c = 0;

            for (var j = cfg.levels - 1; j >= 0; j--) {
                var levelFactor = cfg.factor * radius * ((j + 1) / cfg.levels);

                var area = d3.svg.area()
                    .x(function(d, i) {
                        return levelFactor * (1 - cfg.factor * Math.sin(i * cfg.radians / total));
                    })
                    .x0(function(d, i) {
                        return levelFactor * (1 - cfg.factor * Math.sin(0 * cfg.radians / total));
                    })
                    .y0(function(d, i) {
                        return levelFactor * (1 - cfg.factor * Math.cos(0 * cfg.radians / total));
                    })
                    .y1(function(d, i) {
                        return levelFactor * (1 - cfg.factor * Math.cos(i * cfg.radians / total));
                    })

                g.selectAll(".levels")
                    .data(allAxis)
                    .enter()
                    .append("svg:path")
                    .attr("d", area)
                    .attr("class", "line")
                    .style("stroke", "#3A91C0")
                    .style("stroke-width", "0.3px")
                    .style("fill", cfg.bg_colors[c])
                    .attr("transform", "translate(" + (cfg.w / 2 - levelFactor) + ", " + (cfg.h / 2 - levelFactor) + ")");

                c++;
            }

            series = 0;

            var axis = g.selectAll(".axis")
                .data(allAxis)
                .enter()
                .append("g")
                .attr("class", "axis");


            axis.append("line")
                .attr("x1", cfg.w / 2)
                .attr("y1", cfg.h / 2)
                .attr("x2", function(d, i) {
                    return cfg.w / 2 * (1 - cfg.factor * Math.sin(i * cfg.radians / total));
                })
                .attr("y2", function(d, i) {
                    return cfg.h / 2 * (1 - cfg.factor * Math.cos(i * cfg.radians / total));
                })
                .attr("class", "line")
                .style("stroke", "#3A91C0")
                .style("stroke-width", "1px");

            d.forEach(function(y, x) {

                dataValues = [];
                g.selectAll(".nodes")
                    .data(y, function(j, i) {
                        dataValues.push([
                            cfg.w / 2 * (1 - (parseFloat(Math.max(j.value, 0)) / cfg.maxValue) * cfg.factor * Math.sin(i * cfg.radians / total)),
                            cfg.h / 2 * (1 - (parseFloat(Math.max(j.value, 0)) / cfg.maxValue) * cfg.factor * Math.cos(i * cfg.radians / total))
                        ]);
                    });
                dataValues.push(dataValues[0]);
                g.selectAll(".area")
                    .data([dataValues])
                    .enter()
                    .append("polygon")
                    .attr("class", "radar-chart-serie" + series)
                    .style("stroke-width", "2px")
                    .style("stroke", cfg.color[series])
                    .attr("points", function(d) {
                        var str = "";
                        for (var pti = 0; pti < d.length; pti++) {
                            str = str + d[pti][0] + "," + d[pti][1] + " ";
                        }
                        return str;
                    })
                    .style("fill", function(j, i) {
                        return cfg.color[series]
                    })
                    .style("fill-opacity", cfg.opacityArea)
                    .on('mouseover', function(d) {
                        z = "polygon." + d3.select(this).attr("class");
                        g.selectAll("polygon")
                            .transition(200)
                            .style("fill-opacity", 0.1);
                        g.selectAll(z)
                            .transition(200)
                            .style("fill-opacity", .6);
                    })
                    .on('mouseout', function() {
                        g.selectAll("polygon")
                            .transition(200)
                            .style("fill-opacity", cfg.opacityArea);
                    });
                series++;

            });
            series = 0;
            var r = 0;
            var s = 0;
            var dataId;



            d.forEach(function(y, x) {
                g.selectAll(".nodes")
                    .data(y).enter()
                    .append("svg:circle")
                    .attr("cx", function(j, i) {
                        dataValues.push([
                            cfg.w / 2 * (1 - (parseFloat(Math.max(j.value, 0)) / cfg.maxValue) * cfg.factor * Math.sin(i * cfg.radians / total)),
                            cfg.h / 2 * (1 - (parseFloat(Math.max(j.value, 0)) / cfg.maxValue) * cfg.factor * Math.cos(i * cfg.radians / total))
                        ]);
                        return cfg.w / 2 * (1 - (Math.max(j.value, 0) / cfg.maxValue) * cfg.factor * Math.sin(i * cfg.radians / total));
                    })
                    .attr("cy", function(j, i) {
                        return cfg.h / 2 * (1 - (Math.max(j.value, 0) / cfg.maxValue) * cfg.factor * Math.cos(i * cfg.radians / total));
                    })
                    .attr("data-identifier", function(i) {
                        return r++;
                    })
                    .attr("r", 14)
                    .attr("class", "blue_circle_radar_background");

                g.selectAll(".nodes")
                    .data(y).enter()
                    .append("svg:circle")
                    .attr("cx", function(j, i) {
                        dataValues.push([
                            cfg.w / 2 * (1 - (parseFloat(Math.max(j.value, 0)) / cfg.maxValue) * cfg.factor * Math.sin(i * cfg.radians / total)),
                            cfg.h / 2 * (1 - (parseFloat(Math.max(j.value, 0)) / cfg.maxValue) * cfg.factor * Math.cos(i * cfg.radians / total))
                        ]);
                        return cfg.w / 2 * (1 - (Math.max(j.value, 0) / cfg.maxValue) * cfg.factor * Math.sin(i * cfg.radians / total));
                    })
                    .attr("cy", function(j, i) {
                        return cfg.h / 2 * (1 - (Math.max(j.value, 0) / cfg.maxValue) * cfg.factor * Math.cos(i * cfg.radians / total));
                    })
                    .attr("data-identifier", function(i) {
                        return s++;
                    })
                    .attr("r", 6)
                    .attr("class", "blue_circle_radar")
                    .on('mouseover', function(d) {
                        d3.select(id).selectAll('.blue_circle_radar').classed('selected', false);
                        d3.select(id).selectAll('.blue_circle_radar_background').classed('selected', false);

                        newX = parseFloat(d3.select(this).attr('cx')) - 10;
                        newY = parseFloat(d3.select(this).attr('cy')) - 5;

                        d3.select(this).classed('selected', true);

                        dataId = d3.select(this).attr('data-identifier');

                        d3.select(id).selectAll(".blue_circle_radar_background").each(function(d, i) {
                            if (d3.select(this).attr('data-identifier') == dataId) {
                                d3.select(this).classed('selected', true);
                            }
                        });

                        d3.select(cfg.infoBox).classed('selected', true);
                        d3.select(cfg.infoBox).style('left', parseFloat(d3.select(this).attr('cx')) + 120 + 'px');
                        d3.select(cfg.infoBox).style('top', parseFloat(d3.select(this).attr('cy')) + 7 + 'px');
                        d3.select(cfg.infoBox + " > span:nth-child(1)").html(d.value);
                        d3.select(cfg.infoBox + " > span:nth-child(3)").html(d.axis);

                        z = "polygon." + d3.select(this).attr("class");
                        g.selectAll("polygon")
                            .transition(200)
                            .style("fill-opacity", 0.6);
                        g.selectAll(z)
                            .transition(200)
                            .style("fill-opacity", .6);
                    })
                    .on('mouseout', function() {
                        d3.select(this).classed('selected', false);

                        dataId = d3.select(this).attr('data-identifier');

                        d3.selectAll(".blue_circle_radar_background").each(function(d, i) {
                            if (d3.select(this).attr('data-identifier') == dataId) {
                                d3.select(this).classed('selected', false);
                            }
                        });
                        d3.select(cfg.infoBox).classed('selected', false);
                        g.selectAll("polygon")
                            .transition(200)
                            .style("fill-opacity", cfg.opacityArea);
                    })
                series++;
            });

            var itemToShow;

            d3.select(id).selectAll(".blue_circle_radar").each(function(d, i) {
                if (parseInt(d3.select(this).attr('data-identifier')) == 0) {
                    itemToShow = this;
                }
            });

            function initRadarChart() {
                newX = parseFloat(d3.select(itemToShow).attr('cx')) - 10;
                newY = parseFloat(d3.select(itemToShow).attr('cy')) - 5;

                d3.select(itemToShow).classed('selected', true);

                dataId = d3.select(itemToShow).attr('data-identifier');

                d3.select(id).selectAll(".blue_circle_radar_background").each(function(d, i) {
                    if (d3.select(this).attr('data-identifier') == dataId) {
                        d3.select(this).classed('selected', true);
                    }
                });

                d3.select(cfg.infoBox).classed('selected', true);
                d3.select(cfg.infoBox).style('left', parseFloat(d3.select(itemToShow).attr('cx')) + 120 + 'px');
                d3.select(cfg.infoBox).style('top', parseFloat(d3.select(itemToShow).attr('cy')) - 3 + 'px');
                d3.select(cfg.infoBox + " > span:nth-child(1)").html(d[0][0].value);
                d3.select(cfg.infoBox + " > span:nth-child(3)").html(d[0][0].axis);

                z = "polygon." + d3.select(itemToShow).attr("class");
                g.selectAll("polygon")
                    .transition(200)
                    .style("fill-opacity", 0.6);
                g.selectAll(z)
                    .transition(200)
                    .style("fill-opacity", .6);
            }

            d3.select(id).on('mouseleave', initRadarChart);
            initRadarChart();
        }
    };

});
