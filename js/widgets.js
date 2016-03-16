Array.range = function(n) {
    // Array.range(5) --> [0,1,2,3,4]
    return Array.apply(null, Array(n)).map((x, i) => i);
};

Object.defineProperty(Array.prototype, 'chunk', {
    // Chunking an Array given the numeric parameter.
    value: function(n) {
        return Array.range(Math.ceil(this.length / n)).map((x, i) => this.slice( i * n, i * n + n));
    }
});

function checkStatus(response) {
    // `fetch` doesn't provide an error handling based on status code.
    if (response.status >= 200 && response.status < 300) {
        return response;
    } else {
        const error = new Error(response.statusText);
        error.response = response;
        throw error;
    }
}
function zip(arrays) {
    // Equivalent to `zip()` in Python.
    return arrays[0].map((_, i) => {
        return arrays.map((array) => array[i]);
    });
}
function buildIntegrationFragment(reference) {
    const [kind, ...ids] = reference.split('-');
    const id = ids.join('-');
    const fragment = document.createElement('div');
    fragment.classList.add('embed');
    const help = document.createElement('p');
    help.classList.add('udata-help');
    help.innerHTML = `<a href="#">Copy-paste</a> that code into your
    own HTML and/or <a href="${baseURL}/faq/developer/">read the documentation</a>.`;
    fragment.appendChild(help);
    const textarea = document.createElement('textarea');
    textarea.innerHTML = `<div data-udata-${kind}-id="${id}"></div>
<script src="${scriptURI}" id="udata" async defer></script>`;
    fragment.appendChild(textarea);
    return fragment;
}
function easeCopyPasting(content) {
    const textarea = content.querySelector('textarea');
    textarea.focus();
    textarea.select();
    const help = content.querySelector('.udata-help');
    help.firstChild.addEventListener('click', (e) => {
        e.preventDefault();
        textarea.select();
        document.execCommand('copy');
    });
}
function handleIntegration(event) {
    event.preventDefault();
    const element = event.target;
    const paragraph = element.parentNode;
    const aside = paragraph.parentNode;
    const content = aside.previousElementSibling;
    const article = aside.parentNode;
    const label = element.dataset.label;
    element.dataset.label = element.innerHTML;
    element.innerHTML = label;
    paragraph.classList.toggle('udata-close');
    paragraph.classList.toggle('udata-retweet');
    content.classList.toggle('shrink');
    if (!paragraph.classList.contains('udata-close')) {
        content.removeChild(content.querySelector('.embed'));
    } else {
        content.appendChild(buildIntegrationFragment(article.id));
        easeCopyPasting(content);
    }
}

// Warning: using `Array.from` adds 700 lines once converted through Babel.
const territories = [].slice.call(document.querySelectorAll('[data-udata-territory-id]'));
const datasets = [].slice.call(document.querySelectorAll('[data-udata-dataset-id]'));
// Extract the base URL from the URL to that script.
const parser = document.createElement('a');
const scriptURI = document.querySelector('script#udata').src
parser.href = scriptURI;
const baseURL = `${parser.protocol}//${parser.host}`;
// Keep the chunk > 9 otherwise territories pages will issue more than one query.
territories.concat(datasets).chunk(9).forEach((elements) => {
    const references = elements.map((el) => {
        if (el.hasAttribute('data-udata-territory-id')) {
            const territoryId = el.getAttribute('data-udata-territory-id');
            return `territory-${territoryId}`;
        } else if (el.hasAttribute('data-udata-dataset-id')) {
            const datasetId = el.getAttribute('data-udata-dataset-id');
            return `dataset-${datasetId}`;
        }
    });
    const url = `${baseURL}/api/1/oembeds/?references=${references}`;
    fetch(url)
        .then(checkStatus)
        .then((response) => response.json())
        .then((jsonResponse) => {
            // We match the returned list with the list of elements.
            zip([elements, jsonResponse, references]).forEach(([element, response, id]) => {
                element.innerHTML = response.html;
                document.querySelector(`#${id} .integrate`).addEventListener('click', handleIntegration)
            });
        })
        .catch(console.error.bind(console));
});
