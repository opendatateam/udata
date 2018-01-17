const recoUrl = 'https://raw.githubusercontent.com/etalab/datasets_reco/master/reco_json/';
const maxRecos = 2;

function getDatasetId() {
    const selector = '#json_ld';
    const dataset = JSON.parse(document.querySelector(selector).text);
    return dataset && dataset['@id'];
}

function addRecos(recos) {
    const recoContainer = document.getElementById('dataset-recommendations-container');
    let recoChildContainer, recoChildEmbed;
    recos.splice(0, maxRecos).forEach((reco) => {
        recoChildContainer = document.createElement('div');
        recoChildContainer.classList.add('recommendation');

        recoChildEmbed = document.createElement('div');
        recoChildEmbed.setAttribute('data-udata-dataset-id', reco[0]);

        recoChildContainer.appendChild(recoChildEmbed);
        recoContainer.appendChild(recoChildContainer);
    });
}

function addWidgetScript() {
    const scriptElm = document.createElement('script');
    scriptElm.type = 'application/javascript';
    scriptElm.src = '/static/widgets.js';
    scriptElm.id = 'udata';
    scriptElm.onload = loadDatasets;
    document.body.appendChild(scriptElm);
}

function loadDatasets() {
    udataScript.loadDatasets();
    const recoParent = document.getElementById('dataset-recommendations');
    recoParent.style.display = 'block';
}

function fetchRecos(datasetId) {
    fetch(recoUrl + datasetId + '.json').then((response) => {
        if(response.ok) {
            return response.json();
        }
    }).then((recos) => {
        recos = recos && recos[datasetId];
        if (recos) {
            addRecos(recos);
            addWidgetScript();
        }
    }).catch((err) => {
        console.log('Error while fetching recommendations:', err);
    });
}

global.udataDatasetRecos = {
    load() {
        const datasetId = getDatasetId();
        if (datasetId) {
            fetchRecos(datasetId);
        }
    }
}
