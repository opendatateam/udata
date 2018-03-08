# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from elasticsearch_dsl import analyzer, tokenizer, token_filter, char_filter

# Custom filters for analyzers.
de_stop_filter = token_filter(
    'de_stop_filter', type='stop', stopwords='_german_')
de_stem_filter = token_filter(
    'de_stem_filter', type='stemmer', language='minimal_german')

en_stop_filter = token_filter(
    'en_stop_filter', type='stop', stopwords='_english_')
en_stem_filter = token_filter(
    'en_stem_filter', type='stemmer', language='minimal_english')

es_stop_filter = token_filter(
    'es_stop_filter', type='stop', stopwords='_spanish_')
es_stem_filter = token_filter(
    'es_stem_filter', type='stemmer', language='light_spanish')

pt_stop_filter = token_filter(
    'pt_stop_filter', type='stop', stopwords='_portuguese_')
pt_stem_filter = token_filter(
    'pt_stem_filter', type='stemmer', language='light_portuguese')

fr_stop_filter = token_filter(
    'fr_stop_filter', type='stop', stopwords='_french_')
fr_stem_filter = token_filter(
    'fr_stem_filter', type='stemmer', language='minimal_french')
# Deal with French specific aspects.
fr_elision = token_filter(
    'fr_elision',
    type='elision',
    articles=[
        'l', 'm', 't', 'qu', 'n', 's', 'j', 'd', 'c',
        'jusqu', 'quoiqu', 'lorsqu', 'puisqu'
    ]
)

# Languages related analyzers.
de_analyzer = analyzer(
    'de_analyzer',
    tokenizer=tokenizer('icu_tokenizer'),
    filter=['icu_folding', 'icu_normalizer', de_stop_filter, de_stem_filter],
    char_filter=[char_filter('html_strip')]
)

en_analyzer = analyzer(
    'en_analyzer',
    tokenizer=tokenizer('icu_tokenizer'),
    filter=['icu_folding', 'icu_normalizer', en_stop_filter, en_stem_filter],
    char_filter=[char_filter('html_strip')]
)

es_analyzer = analyzer(
    'es_analyzer',
    tokenizer=tokenizer('icu_tokenizer'),
    filter=['icu_folding', 'icu_normalizer', es_stop_filter, es_stem_filter],
    char_filter=[char_filter('html_strip')]
)

fr_analyzer = analyzer(
    'fr_analyzer',
    tokenizer=tokenizer('icu_tokenizer'),
    filter=['icu_folding', 'icu_normalizer',
            fr_elision, fr_stop_filter, fr_stem_filter],
    char_filter=[char_filter('html_strip')]
)

pt_analyzer = analyzer(
    'pt_analyzer',
    tokenizer=tokenizer('icu_tokenizer'),
    filter=['icu_folding', 'icu_normalizer', pt_stop_filter, pt_stem_filter],
    char_filter=[char_filter('html_strip')]
)

simple = analyzer('simple')
standard = analyzer('standard')


# Custom analysers
analyzers = (de_analyzer, en_analyzer, es_analyzer, fr_analyzer, pt_analyzer)

# Custom filters
filters = (de_stop_filter, de_stem_filter, en_stop_filter, en_stem_filter,
           es_stop_filter, es_stem_filter, fr_stop_filter, fr_stem_filter,
           fr_elision, pt_stop_filter, pt_stem_filter)
