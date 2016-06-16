/* This file is using http://standardjs.com/ */
// `fetch` polyfill added by webpack.
/* global fetch */

// Constants in use within the HTML.
const TERRITORY = 'data-udata-territory'
const TERRITORY_ID = 'data-udata-territory-id'
const DATASET_ID = 'data-udata-dataset-id'

// Helpers
const qS = document.querySelector.bind(document)
const qSA = document.querySelectorAll.bind(document)

// Extract the base URL from the URL of that script.
const parser = document.createElement('a')
const scriptURI = qS('script#udata').src
parser.href = scriptURI
const baseURL = `${parser.protocol}//${parser.host}`

/**
 * Return the `array` chunked by `n`, useful to retrieve all datasets
 * with a minimum of requests.
 * TODO: more clever chunk to retrieve n, then n * 2, then n * 4, etc?
 * in order to display first datasets quickly then load on a minimum
 * of requests.
 */
function chunk (array, n) {
  return Array
    .apply(null, Array(Math.ceil(array.length / n))).map((x, i) => i) // range
    .map((x, i) => array.slice(i * n, i * n + n))
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
<script src="${scriptURI}" id="udata" async defer></script>`
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
function handleIntegration (event) {
  event.preventDefault()
  const element = event.target
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
 * Runner for generators.
 * See https://blog.getify.com/promises-wrong-ways/
 * https://github.com/getify/You-Dont-Know-JS/blob/master/es6%20&%20beyond/ch4.md#generators--promises
 * https://blog.getify.com/not-awaiting-1 & https://blog.getify.com/not-awaiting-2
 */
function run (generator, ...args) {
  const iterator = generator(...args)
  return Promise.resolve()
    .then(function handleNext (value) {
      const next = iterator.next(value)
      return (function handleResult (next) {
        if (next.done) {
          return next.value
        } else {
          return Promise.resolve(next.value)
            .then(
              handleNext,
              (error) => {
                return Promise.resolve(iterator.throw(error))
                  .then(handleResult)
              }
            )
        }
      })(next)
    })
}

/**
 * Using generators + promises.
 * See https://blog.getify.com/promises-wrong-ways/
 * https://github.com/getify/You-Dont-Know-JS/blob/master/es6%20&%20beyond/ch4.md#generators--promises
 * https://blog.getify.com/not-awaiting-1 & https://blog.getify.com/not-awaiting-2
 */
function * fetchJSON (url) {
  const rawResponse = yield fetch(url)
  const validResponse = yield checkStatus(rawResponse)
  return validResponse.json()
}

/**
 * Main function retrieving the HTML code from the API.
 * Keep the chunk > 12 otherwise territories pages will issue more than one query.
 */
function embedDatasets (territories, datasets) {
  chunk(territories.concat(datasets), 12).forEach((elements) => {
    const references = elements.map((el) => {
      if (el.hasAttribute(TERRITORY_ID)) {
        return `territory-${el.dataset.udataTerritoryId}`
      } else if (el.hasAttribute(DATASET_ID)) {
        return `dataset-${el.dataset.udataDatasetId}`
      }
    })
    const url = `${baseURL}/api/1/oembeds/?references=${references}`
    run(fetchJSON, url)
      .then((jsonResponse) => {
        // We match the returned list with the list of elements.
        zip([elements, jsonResponse, references])
          .forEach(([element, response, id]) => {
            element.innerHTML = response.html
            const integrateElement = element.querySelector('.integrate')
            integrateElement.addEventListener('click', handleIntegration)
          })
      }, console.error.bind(console))
  })
}

// If a whole territory is defined, it takes precedence.
// Otherwise fallback on ids.
const territoryElement = qS(`[${TERRITORY}]`)
if (territoryElement) {
  const territorySlug = territoryElement.dataset.udataTerritory
  const territoryId = territorySlug.replace(/-/g, '/')
  const url = `${baseURL}/api/1/spatial/zone/${territoryId}/datasets?dynamic=1`
  run(fetchJSON, url)
    .then((jsonResponse) => {
      // Create a div for each returned item ready to be filled with
      // the usual script dedicated to territories/datasets ids.
      const territories = jsonResponse
        .filter((item) => item.class !== 'Dataset')
        .map((item) => {
          const fragment = document.createElement('div')
          fragment.dataset.udataTerritoryId = `${territorySlug}-${item.id}`
          territoryElement.appendChild(fragment)
          return fragment
        })
      const datasets = jsonResponse
        .filter((item) => item.class === 'Dataset')
        .map((item) => {
          const fragment = document.createElement('div')
          fragment.dataset.udataDatasetId = item.id
          territoryElement.appendChild(fragment)
          return fragment
        })
      embedDatasets(territories, datasets)
    }, console.error.bind(console))
} else {
  // Warning: using `Array.from` adds 700 lines once converted through Babel.
  const territories = [].slice.call(qSA(`[${TERRITORY_ID}]`))
  const datasets = [].slice.call(qSA(`[${DATASET_ID}]`))
  embedDatasets(territories, datasets)
}
