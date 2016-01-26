<style lang="less">
.selectize-zone {
    [data-selectable] {
        border-bottom: 1px solid rgba(0,0,0,0.05);
    }

    .title {
        display: block;
    }

    .code {
        font-size: 11px;
        opacity: 0.8;
        margin-left: 2px;
    }

    .name {
        font-weight: bold;
        margin-right: 5px;
    }

    .level {
        font-size: 12px;
        display: block;
        opacity: 0.5;
        white-space: nowrap;
        width: 100%;
        text-overflow: ellipsis;
        overflow: hidden;
    }

    ul {
        list-style: none;
        margin: 0;
        padding: 0;
        font-size: 10px;

        li {
            margin: 0;
            padding: 0;
            display: inline;
            margin-right: 10px;

            span.value {
                font-weight: bold;
            }
        }
    }
}

.selectize-zone-item {
    .code {
        font-style: italic;
    }
}
</style>

<script>
import Vue from 'vue';
import API from 'api';
import BaseCompleter from 'components/form/base-completer.vue';
import GeoLevels from 'models/geolevels';
import utils from 'utils';


export default {
    name: 'zone-completer',
    mixins: [BaseCompleter],
    ns: 'spatial',
    endpoint: 'suggest_zones',
    data: function() {
        return {
            levels: new GeoLevels()
        }
    },
    selectize: function() {
        return {
            valueField: 'id',
            labelField: 'name',
            searchField: ['name', 'code', 'extraKeys'],
            plugins: ['remove_button'],
            create: function(input, callback) {
                if (utils.isString(input)) {
                    // Need to fetch the real zone
                    // TODO: expose direct full acces to zone by ID
                    API.spatial.spatial_zone({id: input}, (response) => {
                        callback(response.obj);
                    });
                } else {
                    callback(input)
                };
            },
            render: {
                option: (data, escape) => {
                    var opt = [
                            '<div class="selectize-zone">',
                            '<span class="title">',
                            '<span class="name">',
                            escape(data.name),
                            '</span>',
                            '<span class="code">',
                            escape(data.code),
                            '</span>',
                            '</span>',
                            '<span class="level">',
                            this.levelLabel(data),
                            '</span>'
                        ];
                    if (data.keys) {
                        opt.push('<ul>');
                        Object.keys(data.keys).map(function(key) {
                            opt.push('<li><span class="text-uppercase">');
                            opt.push(escape(key));
                            opt.push('</span>: <span class="value">');
                            opt.push(escape(data.keys[key]));
                            opt.push('</span></li>');
                        });
                        opt.push('</ul>');
                    }
                    opt.push('</div>');
                    return opt.join('');
                },
                item: function(data, escape) {
                    return [
                        '<div class="selectize-zone-item">',
                        escape(data.name),
                        ' <span class="code">(',
                        escape(data.code),
                        ')</span></div>'
                    ].join('');
                }
            }
        };
    },
    dataLoaded: function(data) {
        return data.map(function(item) {
            item.extraKeys = Object.keys(item.keys).map(function(key) {
                return item.keys[key];
            });
            return item;
        });
    },
    ready: function() {
        this.levels.fetch();
    },
    methods: {
        levelLabel: function(zone) {
            return this.levels.by_id(zone.level).name;
        }
    }
};
</script>
