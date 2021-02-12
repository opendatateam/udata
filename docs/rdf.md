# RDF

udata has built-in [RDF][] support allowing it to both expose and harvest RDF metadata.
It uses the [Data Catalog Vocabulary][dcat] (or [DCAT][]) as base vocabulary.

## Endpoints

udata exposes instance metadata through different RDF endpoints
and tries to follow some best practices.

*All relative URLs are relative to the udata instance root*

### Content Negotiation

The following formats are supported (default in bold):

| Format             | Extension        | MIME type                                 |
|--------------------|------------------|-------------------------------------------|
| [RDF/XML][rdf-xml] | **xml**, rdf     | **application/rdf+xml**, application/xml  |
| [Turtle][]         | **ttl**          | **text/turle**, application/x-turtle      |
| [Notation3][n3]    | **n3**           | **text/n3**                               |
| [JSON-LD][]        | **jsonld**, json | **application/ld+json**, application/json |
| [N-Triples][]      | **nt**           | **application/n-triples**                 |
| [TriG][]           | **trig**         | **application/trig**                      |

Each endpoint is available through a generic URL which performs content negotiation
and redirects to a set of format specific URLs.
The default format is JSON-LD.


### Organization

Organizations are available through the following URL:

    /organization/{id}/catalog

where `id` is the organization's identifier on the udata instance.

This URL performs content negotiation and redirects to:

    /organization/{id}/catalog.{format}

It is exposed as a [DCAT Catalog][dcat-catalog] and a [Hydra Collection][hydra-collection]
This allows pagination through the `hydra:PartialCollectionView` class.

The organization's catalog embeds the organization's datasets.


### Dataset

Datasets are available through the following URL:

    /dataset/{id}/rdf

where `id` is the dataset's identifier on the udata instance.

This URL performs content negotiation and redirects to:

    /dataset/{id}/rdf.{format}

The dataset pages serves as an identifier and performs content negotiation too,
so the following URLs will all redirect to the same RDF endpoint:

    /dataset/{id}
    /dataset/{slug}
    /{lang}/dataset/{id}
    /{lang}/dataset/{slug}


A Dataset is exposed as a [DCAT Dataset][dcat-dataset],
a Resource as [DCAT Distribution][dcat-distribution]
and fields are mapped according to:

| Dataset           | dcat:Dataset            | notes |
|-------------------|-------------------------|-------|
| id                | dct:identifier          |       |
| title             | dct:title               |       |
| description       | dct:description         |       |
| tags              | dct:keyword             |       |
| created_at        | dct:issued              |       |
| last_modified     | dct:modified            |       |
| resources         | dcat:distribution       |       |
| temporal_coverage | dct:temporal            | Uses schema.org startDate and endDate |
| frequency         | dct:accrualPeriodicity  | Frequencies without Dublin Core equivalent are mapped to the closest one |
| license           | dct:license + dct:right | License URL in dct:license and license label in dct:right |

| Resource          | dcat:Distribution       | notes |
|-------------------|-------------------------|-------|
| id                | dct:identifier          |       |
| title             | dct:title               |       |
| description       | dct:description         |       |
| url               | dcat:downloadURL        | as URI reference |
| permanent url     | dcat:accessURL          | as URI reference |
| published         | dct:issued              |       |
| last_modified     | dct:modified            |       |
| format            | dct:format              |       |
| mime              | dcat:mediaType          |       |
| filesize          | dcat:bytesSize          |       |
| checksum          | spdx:checksum           |       |

| TemporalCoverage | dct:PeriodOfTime |
|------------------|------------------|
| start            | schema:startDate |
| end              | schema:endDate   |

| Checksum | spdx:Checksum      |
|----------|--------------------|
| type     | spdx:algorithm     |
| value    | spdx:checksumValue |


### Catalog

The site catalog is exposed through:

    /catalog

and performs content negotiation to

    /catalog.{format}

It is exposed as a [DCAT Catalog][dcat-catalog] and a [Hydra Collection][hydra-collection]
This allows pagination through the `hydra:PartialCollectionView` class.


### Dataportal

There is a work in progress [Dataportal specification][dataportal] but as many sites
already use this formalism,
the catalog is also available (as a redirect) on the following URL:

    /data.{format}

where format is one of the supported format extensions.

### JSON-LD context

To reduce payload and increase human readbility,
udata exposes a JSON-LD context and uses it in its serialization.
This context is available on:

    /context.jsonld

## Harvester

udata can harvest other RDF/DCAT enabled data portals with the [DCAT Harvester](harvesting.md#dcat).


## References

The udata rdf implementation and its harvester were created using these references:

- [Official DCAT Vocabulary documentation][dcat]
- [European DCAT-AP documentation][dcat-ap]
- [CKAN DCAT extension][ckanext-dcat]
- [Gov UK references][gov-uk-references]
- [Data.gov.uk guidance][gov-uk-guidance]

The used namespaces are:

- dct: <http://purl.org/dc/terms/>
- dcat: <http://www.w3.org/ns/dcat#>
- foaf: <http://xmlns.com/foaf/0.1/>
- hydra: <http://www.w3.org/ns/hydra/core#>
- schema: <http://schema.org/>
- spdx: <http://spdx.org/rdf/terms#>
- freq: <http://purl.org/cld/freq/>
- scv: <http://purl.org/NET/scovo#>


[rdf]: https://www.w3.org/RDF/
[rdf-xml]: https://www.w3.org/TR/rdf-syntax-grammar/
[turtle]: https://www.w3.org/TR/turtle/
[n3]: https://www.w3.org/TeamSubmission/n3/
[n-triples]: https://www.w3.org/TR/n-triples/
[trig]: https://www.w3.org/TR/trig/
[json-ld]: https://json-ld.org/
[dcat]: https://www.w3.org/TR/vocab-dcat/
[dataportal]: http://spec.dataportals.org/
[dcat-dataset]: https://www.w3.org/TR/vocab-dcat/#Class:_Dataset
[dcat-catalog]: https://www.w3.org/TR/vocab-dcat/#Class:_Catalog
[dcat-distribution]: https://www.w3.org/TR/vocab-dcat/#Class:_Distribution
[hydra-collection]: http://www.hydra-cg.com/spec/latest/core/#collections
[dcat-ap]: https://joinup.ec.europa.eu/asset/dcat_application_profile/
[ckanext-dcat]: https://github.com/ckan/ckanext-dcat
[gov-uk-references]: http://reference.data.gov.uk/
[gov-uk-guidance]: http://guidance.data.gov.uk/
