/*
The aim of that script is to provide a way to embed
a dataset, many datasets or all datasets for a given
territory.

E.g.:

<div data-udata-dataset-id=5715ef5fc751df11b82015f8></div>
<script src="http://example.com/static/widgets.js" id=udata
  async defer onload=udataScript.load()></script>

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

/**
 * Extract the base URL from the URL of the current script,
 * targeted with `selector`.
 */
function extractURLs (selector) {
  const parser = document.createElement('a')
  const scriptURL = document.querySelector(selector).src
  parser.href = scriptURL
  const baseURL = `${parser.protocol}//${parser.host}`
  return {scriptURL, baseURL}
}

const {scriptURL, baseURL} = extractURLs('script#udata')

/**
 * Remove French diacritics from a given string `str`. Adapted from:
 * https://github.com/NaturalNode/natural/blob/master/lib/natural/normalizers/remove_diacritics.js
 */
function removeDiacritics (str) {
  const rules = [
    {'base': 'A', 'letters': /[\u0041\u24B6\uFF21\u00C0\u00C1\u00C2\u1EA6\u1EA4\u1EAA\u1EA8\u00C3\u0100\u0102\u1EB0\u1EAE\u1EB4\u1EB2\u0226\u01E0\u00C4\u01DE\u1EA2\u00C5\u01FA\u01CD\u0200\u0202\u1EA0\u1EAC\u1EB6\u1E00\u0104\u023A\u2C6F]/g},
    {'base': 'E', 'letters': /[\u0045\u24BA\uFF25\u00C8\u00C9\u00CA\u1EC0\u1EBE\u1EC4\u1EC2\u1EBC\u0112\u1E14\u1E16\u0114\u0116\u00CB\u1EBA\u011A\u0204\u0206\u1EB8\u1EC6\u0228\u1E1C\u0118\u1E18\u1E1A\u0190\u018E]/g},
    {'base': 'I', 'letters': /[\u0049\u24BE\uFF29\u00CC\u00CD\u00CE\u0128\u012A\u012C\u0130\u00CF\u1E2E\u1EC8\u01CF\u0208\u020A\u1ECA\u012E\u1E2C\u0197]/g},
    {'base': 'O', 'letters': /[\u004F\u24C4\uFF2F\u00D2\u00D3\u00D4\u1ED2\u1ED0\u1ED6\u1ED4\u00D5\u1E4C\u022C\u1E4E\u014C\u1E50\u1E52\u014E\u022E\u0230\u00D6\u022A\u1ECE\u0150\u01D1\u020C\u020E\u01A0\u1EDC\u1EDA\u1EE0\u1EDE\u1EE2\u1ECC\u1ED8\u01EA\u01EC\u00D8\u01FE\u0186\u019F\uA74A\uA74C]/g},
    {'base': 'OE', 'letters': /[\u0152]/g},
    {'base': 'U', 'letters': /[\u0055\u24CA\uFF35\u00D9\u00DA\u00DB\u0168\u1E78\u016A\u1E7A\u016C\u00DC\u01DB\u01D7\u01D5\u01D9\u1EE6\u016E\u0170\u01D3\u0214\u0216\u01AF\u1EEA\u1EE8\u1EEE\u1EEC\u1EF0\u1EE4\u1E72\u0172\u1E76\u1E74\u0244]/g},
    {'base': 'a', 'letters': /[\u0061\u24D0\uFF41\u1E9A\u00E0\u00E1\u00E2\u1EA7\u1EA5\u1EAB\u1EA9\u00E3\u0101\u0103\u1EB1\u1EAF\u1EB5\u1EB3\u0227\u01E1\u00E4\u01DF\u1EA3\u00E5\u01FB\u01CE\u0201\u0203\u1EA1\u1EAD\u1EB7\u1E01\u0105\u2C65\u0250]/g},
    {'base': 'e', 'letters': /[\u0065\u24D4\uFF45\u00E8\u00E9\u00EA\u1EC1\u1EBF\u1EC5\u1EC3\u1EBD\u0113\u1E15\u1E17\u0115\u0117\u00EB\u1EBB\u011B\u0205\u0207\u1EB9\u1EC7\u0229\u1E1D\u0119\u1E19\u1E1B\u0247\u025B\u01DD]/g},
    {'base': 'i', 'letters': /[\u0069\u24D8\uFF49\u00EC\u00ED\u00EE\u0129\u012B\u012D\u00EF\u1E2F\u1EC9\u01D0\u0209\u020B\u1ECB\u012F\u1E2D\u0268\u0131]/g},
    {'base': 'o', 'letters': /[\u006F\u24DE\uFF4F\u00F2\u00F3\u00F4\u1ED3\u1ED1\u1ED7\u1ED5\u00F5\u1E4D\u022D\u1E4F\u014D\u1E51\u1E53\u014F\u022F\u0231\u00F6\u022B\u1ECF\u0151\u01D2\u020D\u020F\u01A1\u1EDD\u1EDB\u1EE1\u1EDF\u1EE3\u1ECD\u1ED9\u01EB\u01ED\u00F8\u01FF\u0254\uA74B\uA74D\u0275]/g},
    {'base': 'oe', 'letters': /[\u0153]/g},
    {'base': 'u', 'letters': /[\u0075\u24E4\uFF55\u00F9\u00FA\u00FB\u0169\u1E79\u016B\u1E7B\u016D\u00FC\u01DC\u01D8\u01D6\u01DA\u1EE7\u016F\u0171\u01D4\u0215\u0217\u01B0\u1EEB\u1EE9\u1EEF\u1EED\u1EF1\u1EE5\u1E73\u0173\u1E77\u1E75\u0289]/g}
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
  return Array
    .apply(null, Array(Math.ceil(array.length / n)))
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
    if (!timeout) func(...args)
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
<script src="${scriptURL}" id="udata" async defer onload="udataScript.load()"></script>`
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
function toggleIntegration (event) {
  event.preventDefault()
  const element = event.target
  // TODO: use dedicated classes instead of fragile DOM traversal.
  const paragraph = element.parentNode
  const aside = paragraph.parentNode
  const content = aside.previousElementSibling
  const article = aside.parentNode
  const label = element.dataset.label
  element.dataset.label = element.innerHTML
  element.innerHTML = label
  paragraph.classList.toggle('udata-close')
  paragraph.classList.toggle('udata-code')
  content.classList.toggle('shrink')
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
function embedDatasetChunk (datasetChunk, dataTerritoryIdAttr, dataDatasetIdAttr) {
  const references = datasetChunk.map((el) => {
    if (el.hasAttribute(dataTerritoryIdAttr)) {
      return `territory-${el.dataset[camelCaseData(dataTerritoryIdAttr)]}`
    } else if (el.hasAttribute(dataDatasetIdAttr)) {
      return `dataset-${el.dataset[camelCaseData(dataDatasetIdAttr)]}`
    }
  })
  const url = `${baseURL}/api/1/oembeds/?references=${references.join(',')}`
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
          integrateDataset.addEventListener('click', toggleIntegration)
        })
      return datasetChunk
    })
    .catch(console.error.bind(console))
}

/**
 * Main function retrieving the HTML code from the API.
 * Keep the chunk > 12 otherwise territories pages will issue more than one query.
 */
function embedDatasets (territories, datasets, dataTerritoryIdAttr, dataDatasetIdAttr) {
  const items = territories.concat(datasets)
  const chunkBy = 12
  const promises = chunk(items, chunkBy)
    .map((datasetChunk) =>
      embedDatasetChunk(datasetChunk, dataTerritoryIdAttr, dataDatasetIdAttr))
  Promise.all(promises)
    .then((chunks) => {
      // Flatten the array of datasets arrays.
      const datasets = [].concat(...chunks)
      window.dispatchEvent(
        new CustomEvent(
          'udataset.loaded', {
            detail: {
              message: 'uData datasets fully loaded.',
              time: new Date(),
              datasets: datasets
            },
            bubbles: true,
            cancelable: true
          }
        )
      )
    })
    .catch(console.error.bind(console))
}

/**
 * Display only matching datasets given the value of the search input.
 */
function filterDatasets (territoryElement, event, datasets, initialDatasets) {
  const searchValue = event.target.value
  if (searchValue.length < 3) {
    territoryElement.innerHTML = initialDatasets
    return
  }
  const scoredDatasets = datasets.map((dataset) => {
    const title = removeDiacritics(dataset.querySelector('.udata-title').innerText)
    return {
      dataset: dataset,
      score: title.score(removeDiacritics(searchValue))
    }
  })
  const filteredScoredResults = scoredDatasets.filter((result) => result.score > 0)
  filteredScoredResults.sort((a, b) => a.score < b.score)
  if (filteredScoredResults) {
    territoryElement.innerHTML = ''
    filteredScoredResults.forEach((result) =>
      territoryElement.appendChild(result.dataset)
    )
  } else {
    territoryElement.innerHTML = initialDatasets
  }
}

/**
 * Insert the styled search input to the DOM
 * which filters displayed datasets on `keydown`.
 */
function insertSearchInput (event, territoryElement) {
  const datasets = event.detail.datasets
  const initialDatasets = territoryElement.innerHTML
  const searchNode = document.createElement('input')
  searchNode.placeholder = 'Filter datasets'
  searchNode.style.display = 'block'
  searchNode.style.boxSizing = 'border-box'
  searchNode.style.width = '100%'
  searchNode.style.margin = '1em'
  searchNode.style.padding = '.1em'
  territoryElement.parentNode.insertBefore(searchNode, territoryElement)
  // Do not refresh too soon while the user is typing.
  const debouncedFilterDatasets = debounce((event) =>
    filterDatasets(territoryElement, event, datasets, initialDatasets)
  )
  searchNode.addEventListener('keydown', debouncedFilterDatasets)
}

global.udataScript = {

  /**
   * Load territories and datasets from the API given the set
   * data-attributes `dataTerritoryIdAttr` and
   * `dataDatasetIdAttr` within the DOM.
   */
  load (dataTerritoryIdAttr = 'data-udata-territory-id',
        dataDatasetIdAttr = 'data-udata-dataset-id') {
    // Warning: using `Array.from` adds 700 lines once converted through Babel.
    const territories = [].slice.call(document.querySelectorAll(`[${dataTerritoryIdAttr}]`))
    const datasets = [].slice.call(document.querySelectorAll(`[${dataDatasetIdAttr}]`))
    embedDatasets(territories, datasets, dataTerritoryIdAttr, dataDatasetIdAttr)
  },

  /**
   * Load datasets for a given territory from the API given the set
   * data-attribute `dataTerritoryAttr` within the DOM.
   * Optionally you can customize data-attributes dynamically
   * inserted for territories and datasets using
   * `dataTerritoryIdAttr` and `dataDatasetIdAttr`.
   *
   * The `size` parameter limits the number of loaded datasets.
   * The `withSearch` parameter optionally loads an input
   * allowing the user to filter currently displayed datasets.
   */
  loadTerritory (size = 100,
                 withSearch = false,
                 dataTerritoryAttr = 'data-udata-territory',
                 dataTerritoryIdAttr = 'data-udata-territory-id',
                 dataDatasetIdAttr = 'data-udata-dataset-id') {
    const territoryElement = document.querySelector(`[${dataTerritoryAttr}]`)
    const territorySlug = territoryElement.dataset[camelCaseData(dataTerritoryAttr)]
    const territoryId = territorySlug.replace(/-/g, '/')
    const url = `${baseURL}/api/1/spatial/zone/${territoryId}/datasets?dynamic=1&size=${size}`
    fetchJSON(url)
      .then((territoriesAndDatasets) => {
        // Create a div for each returned item ready to be filled with
        // the usual script dedicated to territories/datasets ids.
        const territories = territoriesAndDatasets
          .filter((item) => item.class !== 'Dataset')
          .map((item) => {
            const fragment = document.createElement('div')
            fragment.dataset[camelCaseData(dataTerritoryIdAttr)] = `${territorySlug}-${item.id}`
            territoryElement.appendChild(fragment)
            return fragment
          })
        const datasets = territoriesAndDatasets
          .filter((item) => item.class === 'Dataset')
          .map((item) => {
            const fragment = document.createElement('div')
            fragment.dataset[camelCaseData(dataDatasetIdAttr)] = item.id
            territoryElement.appendChild(fragment)
            return fragment
          })
        embedDatasets(territories, datasets, dataTerritoryIdAttr, dataDatasetIdAttr)
      })
      .catch(console.error.bind(console))
    if (withSearch) {
      window.addEventListener('udataset.loaded', (event) =>
        insertSearchInput(event, territoryElement)
      )
    }
  }
}
