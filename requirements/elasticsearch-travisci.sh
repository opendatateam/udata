#!/bin/bash
wget https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-1.1.0.deb
dpkg -i elasticsearch-1.1.0.deb
service elasticsearch start
/usr/share/elasticsearch/bin/plugin -install elasticsearch/elasticsearch-analysis-icu/2.0.0
