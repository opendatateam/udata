/*
The aim of that script is to provide a way to embed
a dataset, many datasets or all datasets for a given
territory.

E.g.:

<div data-udata-dataset-id=5715ef5fc751df11b82015f8></div>
<script src="http://example.com/static/widgets.js" id=udata
  async defer onload=udataScript.loadDatasets()></script>

You can customize the name of the data attribute which
stores the id of the dataset within the loader but you must
set `udata` as the id of the script tag that loads this file.
*/

/* This file is using http://standardjs.com/ */
/* global fetch, CustomEvent */

// In use for optionally filtering datasets once loaded.
// Adds `.score()` to the prototype of String.
import 'string_score'
// Polyfill to be able to use `fetch` on IE and Safari.
import 'whatwg-fetch'

// Constants in use within the HTML to store ids.
const DATA_ORGANIZATION = 'data-udata-organization'
const DATA_TERRITORY = 'data-udata-territory'
const DATA_TERRITORY_ID = 'data-udata-territory-id'
const DATA_DATASET_ID = 'data-udata-dataset-id'

// Name of the event triggered when all datasets are loaded.
const DATASETS_LOADED_EVENT_NAME = 'udataset:loaded'

// Keep the chunk > 12 otherwise territories pages
// will issue more than one query.
const CHUNK_BY = 12
// TODO: add pagination, for the moment arbitrary limit.
const _MAX_SIZE = 50

/**
 * Extract the base URL from the URL of the current script,
 * targeted with `selector`.
 */
function extractURLs (selector) {
  const parser = document.createElement('a')
  const scriptURL = document.querySelector(selector).src
  parser.href = scriptURL
  const baseURL = `${parser.protocol}//${parser.host}`
  return [scriptURL, baseURL]
}

// Build URLs.
const [scriptURL, baseURL] = extractURLs('script#udata')
const apiURL = `${baseURL}/api/1/`

/**
 * Remove only French diacritics and special chars from a given string `str`.
 */
function removeDiacritics (str) {
  const rules = [
    {'base': 'A', 'letters': /[À]/g},
    {'base': 'E', 'letters': /[ÉÊÈ]/g},
    {'base': 'I', 'letters': /[Ï]/g},
    {'base': 'O', 'letters': /[Ô]/g},
    {'base': 'OE', 'letters': /[Œ]/g},
    {'base': 'U', 'letters': /[ÛÙ]/g},
    {'base': 'a', 'letters': /[à]/g},
    {'base': 'e', 'letters': /[éêè]/g},
    {'base': 'i', 'letters': /[ï]/g},
    {'base': 'o', 'letters': /[ô]/g},
    {'base': 'oe', 'letters': /[œ]/g},
    {'base': 'u', 'letters': /[ûù]/g},
    {'base': '', 'letters': /[\])}'’,.\-—–[{(]/g}
  ]
  rules.forEach((rule) => {
    str = str.replace(rule.letters, rule.base)
  })
  return str
}

/**
 * In use for dynamic data attributes get/set.
 * from `data-udata-territory` to `udataTerritory`.
 */
function camelCaseData (dataAttributeString) {
  // Remove `data-` then camelCase it.
  return dataAttributeString.substr(5)
    .replace(/-(.)/g, (match, group1) => group1.toUpperCase())
}

/**
 * Return the `array` chunked by `n`, useful to retrieve all datasets
 * with a minimum of requests.
 * TODO: more clever chunk to retrieve n, then n * 2, then n * 4, etc?
 * in order to display first datasets quickly then load on a minimum
 * of requests.
 */
function chunk (array, n) {
  return Array(...Array(Math.ceil(array.length / n)))
    .map((x, i) => i)
    .map((x, i) => array.slice(i * n, i * n + n))
}

/**
 * Return a function, that, as long as it continues to be invoked,
 * will not be triggered. The function will be called after
 * it stops being called for `wait` milliseconds. Inspired by:
 * https://davidwalsh.name/javascript-debounce-function
 */
function debounce (func, wait = 350) {
  let timeout
  return (...args) => {
    clearTimeout(timeout)
    timeout = setTimeout(() => {
      timeout = null
      func(...args)
    }, wait)
  }
}

/**
 * `fetch` doesn't provide an error handling based on status code.
 */
function checkStatus (response) {
  if (response.status >= 200 && response.status < 300) {
    return response
  } else {
    const error = new Error(response.statusText)
    error.response = response
    throw error
  }
}

/**
 * Return a promisified JSON response from an API URL
 * if status code is correct.
 */
function fetchJSON (url) {
  return fetch(url)
    .then(checkStatus)
    .then((response) => response.json())
}

/**
 * Equivalent to `zip()` in Python.
 */
function zip (arrays) {
  return arrays[0].map((_, i) => arrays.map((array) => array[i]))
}

/**
 * Return the fragment to embed the current dataset in another page.
 */
function buildIntegrationFragment (reference) {
  const [kind, ...ids] = reference.split('-')
  const id = ids.join('-')
  const fragment = document.createElement('div')
  fragment.classList.add('embed')
  const help = document.createElement('p')
  help.classList.add('udata-help')
  help.innerHTML = `<a href="#">Copy-paste</a> that code into your
    own HTML and/or <a href="${baseURL}/faq/developer/">read the documentation</a>.`
  fragment.appendChild(help)
  const textarea = document.createElement('textarea')
  textarea.innerHTML = `<div data-udata-${kind}-id="${id}"></div>
<script src="${scriptURL}" id="udata" async defer
onload="udataScript.loadDatasets()"></script>`
  fragment.appendChild(textarea)
  return fragment
}

/**
 * Handle the "save on clipboard" capability.
 */
function easeCopyPasting (content) {
  const textarea = content.querySelector('textarea')
  textarea.focus()
  textarea.select()
  const help = content.querySelector('.udata-help')
  help.firstChild.addEventListener('click', (e) => {
    e.preventDefault()
    textarea.select()
    document.execCommand('copy')
  })
}

/**
 * Display/hide the integration box for embeds.
 */
function toggleIntegration (event, dataset) {
  event.preventDefault()
  const paragraph = dataset.querySelector('.udata-code, .udata-close')
  const content = dataset.querySelector('.udata-content')
  const article = dataset.querySelector('.dataset-card')
  const el = event.target
  ;[el.dataset.label, el.innerHTML] = [el.innerHTML, el.dataset.label]
  paragraph.classList.toggle('udata-close')
  paragraph.classList.toggle('udata-code')
  content.classList.toggle('js-hide')
  if (!paragraph.classList.contains('udata-close')) {
    content.removeChild(content.querySelector('.embed'))
  } else {
    content.appendChild(buildIntegrationFragment(article.id))
    easeCopyPasting(content)
  }
}

/**
 * Fetch OEmbeded representations of `datasetChunk`
 */
function embedDatasetChunk (datasetChunk) {
  const references = datasetChunk.map((el) => {
    if (el.hasAttribute(DATA_TERRITORY_ID)) {
      return `territory-${el.dataset[camelCaseData(DATA_TERRITORY_ID)]}`
    } else if (el.hasAttribute(DATA_DATASET_ID)) {
      return `dataset-${el.dataset[camelCaseData(DATA_DATASET_ID)]}`
    }
  })
  const url = `${apiURL}oembeds/?references=${references.join(',')}`
  // Warning: if you are tempted to use generators instead of chaining
  // promises, you'll have to use babel-polyfill which adds 300 Kb
  // once the file is converted to ES5.
  return fetchJSON(url)
    .then((datasetsOEmbededList) => {
      // We match the returned list with the list of datasetChunk.
      zip([datasetChunk, datasetsOEmbededList])
        .forEach(([dataset, response]) => {
          dataset.innerHTML = response.html
          const integrateDataset = dataset.querySelector('.integrate')
          integrateDataset.addEventListener('click', (event) =>
            toggleIntegration(event, dataset)
          )
        })
      return datasetChunk
    })
    .catch(console.error.bind(console))
}

/**
 * Embed each chunk of `datasets`, then dispatch an event.
 */
function embedDatasets (datasets) {
  const promises = chunk(datasets, CHUNK_BY)
    .map((datasetChunk) => embedDatasetChunk(datasetChunk))
  return Promise.all(promises)
    .then((chunks) => {
      // Flatten the array of datasets arrays.
      const datasets = [].concat(...chunks)
      let event
      if (typeof window.CustomEvent === 'function') {
        event = new CustomEvent(DATASETS_LOADED_EVENT_NAME, {
          detail: { datasets },
          bubbles: true,
          cancelable: true
        })
      } else {
        // IE 11 support.
        event = document.createEvent('HTMLEvents')
        event.initEvent(DATASETS_LOADED_EVENT_NAME, true, true)
        event.detail = { datasets }
      }
      window.dispatchEvent(event)
      return datasets
    })
    .catch(console.error.bind(console))
}

/**
 * Display only matching datasets given the value of the search input.
 */
function filterDatasets (element, event, datasets, initialDatasets) {
  const searchValue = event.target.value
  if (searchValue.length < 3) {
    element.innerHTML = initialDatasets
    return
  }
  const scoredDatasets = datasets.map((dataset) => {
    const title = removeDiacritics(dataset.querySelector('.udata-title a').title)
    return {
      dataset: dataset,
      score: title.score(removeDiacritics(searchValue))
    }
  })
  // Only keep results with high scores, then sort (highest first).
  const filteredScoredResults = scoredDatasets.filter((result) => result.score > 0.3)
  filteredScoredResults.sort((a, b) => a.score < b.score)
  if (filteredScoredResults) {
    element.innerHTML = ''
    filteredScoredResults.forEach((result) =>
      element.appendChild(result.dataset)
    )
  } else {
    element.innerHTML = initialDatasets
  }
}

/**
 * Insert the styled search input to the DOM
 * which filters displayed datasets on `keydown`.
 */
function insertSearchInput (event, element) {
  // Happen when we reload a territory manually.
  if (!element.parentNode) return
  const datasets = event.detail.datasets
  const initialDatasets = element.innerHTML
  const searchNode = document.createElement('input')
  searchNode.placeholder = 'Filter datasets'
  searchNode.style.display = 'block'
  searchNode.style.boxSizing = 'border-box'
  searchNode.style.width = '90%'
  searchNode.style.maxWidth = '1000px'
  searchNode.style.margin = '1em'
  searchNode.style.padding = '.1em'
  element.parentNode.insertBefore(searchNode, element)
  // Do not refresh too soon while the user is typing.
  const debouncedFilterDatasets = debounce((event) =>
    filterDatasets(element, event, datasets, initialDatasets)
  )
  searchNode.addEventListener('keydown', debouncedFilterDatasets)
}

global.udataScript = {

  /**
   * Load dataset(s) and/or dynamically generated one(s) from the API.
   */
  loadDatasets () {
    // Warning: using `Array.from` adds 700 lines once converted through Babel.
    const territories = [].slice.call(document.querySelectorAll(`[${DATA_TERRITORY_ID}]`))
    const datasets = [].slice.call(document.querySelectorAll(`[${DATA_DATASET_ID}]`))
    return embedDatasets([...territories, ...datasets])
  },

  /**
   * Load datasets for a given territory.
   *
   * The `withDynamic` parameter loads dynamically generated datasets.
   * The `withSearch` parameter optionally loads an input
   * allowing the user to filter currently displayed datasets.
   */
  loadTerritory ({withDynamic = true, withSearch = false} = {}) {
    const territoryElement = document.querySelector(`[${DATA_TERRITORY}]`)
    const territorySlug = territoryElement.dataset[camelCaseData(DATA_TERRITORY)]
    const territoryId = territorySlug.replace(/-/g, '/')
    const url = `${apiURL}spatial/zone/${territoryId}/datasets?dynamic=${withDynamic}&size=${_MAX_SIZE}`
    return fetchJSON(url)
      .then((territoriesAndDatasets) => {
        // Create a div for each returned item ready to be filled with
        // the usual script dedicated to territories/datasets ids.
        const territories = territoriesAndDatasets
          .filter((item) => item.class !== 'Dataset')
          .map((item) => {
            const fragment = document.createElement('div')
            fragment.dataset[camelCaseData(DATA_TERRITORY_ID)] = `${territorySlug}-${item.id}`
            territoryElement.appendChild(fragment)
            return fragment
          })
        const datasets = territoriesAndDatasets
          .filter((item) => item.class === 'Dataset')
          .map((item) => {
            const fragment = document.createElement('div')
            fragment.dataset[camelCaseData(DATA_DATASET_ID)] = item.id
            territoryElement.appendChild(fragment)
            return fragment
          })
        if (withSearch) {
          window.addEventListener(DATASETS_LOADED_EVENT_NAME, (event) =>
            insertSearchInput(event, territoryElement)
          )
        }
        return embedDatasets([...territories, ...datasets])
      })
      .catch(console.error.bind(console))
  },

  /**
   * Load datasets for a given organization.
   *
   * The `withSearch` parameter optionally loads an input
   * allowing the user to filter currently displayed datasets.
   */
  loadOrganization ({withSearch = false} = {}) {
    const organizationElement = document.querySelector(`[${DATA_ORGANIZATION}]`)
    const organizationId = organizationElement.dataset[camelCaseData(DATA_ORGANIZATION)]
    const url = `${apiURL}organizations/${organizationId}/datasets/?size=${_MAX_SIZE}`
    return fetchJSON(url)
      .then((datasets) => {
        // Create a div for each returned item ready to be filled with
        // the usual script dedicated to datasets ids.
        datasets = datasets
          .map((item) => {
            const fragment = document.createElement('div')
            fragment.dataset[camelCaseData(DATA_DATASET_ID)] = item.id
            organizationElement.appendChild(fragment)
            return fragment
          })
        if (withSearch) {
          window.addEventListener(DATASETS_LOADED_EVENT_NAME, (event) =>
            insertSearchInput(event, organizationElement)
          )
        }
        return embedDatasets(datasets)
      })
      .catch(console.error.bind(console))
  }
}
