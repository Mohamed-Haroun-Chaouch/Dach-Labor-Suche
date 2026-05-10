// Map initialisieren (Zentriert auf Deutschland/DACH)
const map = L.map('map').setView([51.1657, 10.4515], 6);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 19
}).addTo(map);

// NEU: MarkerClusterGroup statt normalem LayerGroup
const markersCluster = L.markerClusterGroup({
    chunkedLoading: true,
    spiderfyOnMaxZoom: true
});
map.addLayer(markersCluster);

let allProviders = [];

// NEU: Koordinaten für unsere Städte (Fly-To)
const cityCoordinates = {
    "DACH": { lat: 51.1657, lng: 10.4515, zoom: 6 },
    "Berlin": { lat: 52.5200, lng: 13.4050, zoom: 11 },
    "Hannover": { lat: 52.3759, lng: 9.7320, zoom: 12 },
    "München": { lat: 48.1351, lng: 11.5820, zoom: 12 },
    "Hamburg": { lat: 53.5511, lng: 9.9937, zoom: 11 },
    "Frankfurt": { lat: 50.1109, lng: 8.6821, zoom: 11 },
    "Köln": { lat: 50.9375, lng: 6.9603, zoom: 11 },
    "Stuttgart": { lat: 48.7758, lng: 9.1829, zoom: 11 }
};

// Dropdown Event Listener
document.getElementById('city-dropdown').addEventListener('change', (e) => {
    const city = e.target.value;
    const coords = cityCoordinates[city];
    if (coords) {
        // Die FlyTo Funktion von Leaflet
        map.flyTo([coords.lat, coords.lng], coords.zoom, {
            animate: true,
            duration: 1.5
        });
    }
});

// Daten laden
fetch('../data/data.json')
    .then(response => response.json())
    .then(data => {
        allProviders = data;
        renderMarkers('all');
    })
    .catch(error => console.error('Error loading data:', error));

function renderMarkers(filterCategory) {
    // Cluster leeren
    markersCluster.clearLayers();

    let filteredData = allProviders;

    // 1. Nach Kategorie filtern (Radio Buttons)
    if (filterCategory !== 'all') {
        filteredData = filteredData.filter(provider => provider.categories.includes(filterCategory));
    }

    // 2. NEU: Nach Qualität filtern (Checkbox)
    const onlyVerified = document.getElementById('filter-verified').checked;
    if (onlyVerified) {
        filteredData = filteredData.filter(provider => provider.meta.verified_manually === true);
    }

    document.getElementById('provider-count').innerText = filteredData.length;

    filteredData.forEach(provider => {
        if (!provider.coordinates || !provider.coordinates.lat || !provider.coordinates.lng) return;

        const isDexa = provider.categories.includes('dexa');
        const marker = L.marker([provider.coordinates.lat, provider.coordinates.lng]);

        const verifiedBadge = provider.meta.verified_manually 
            ? '<span class="badge verified">✅ Verified</span>' 
            : '<span class="badge unverified">⚠️ Unverified (Needs Check)</span>';

        const categoryText = isDexa ? 'DEXA Scan' : 'Blood Lab';

        const phoneHtml = provider.contact.phone ? `📞 ${provider.contact.phone}<br>` : '';
        const websiteHtml = provider.contact.website ? `🌐 <a href="${provider.contact.website}" target="_blank">Zur Website</a>` : '';

        const popupContent = `
            <div class="custom-popup">
                ${verifiedBadge}
                <h3>${provider.name}</h3>
                <p><strong>Type:</strong> ${categoryText}</p>
                <p><strong>Adresse:</strong> ${provider.address.full_address}</p>
                <div class="popup-contact">
                    ${phoneHtml}
                    ${websiteHtml}
                </div>
                <hr style="margin: 8px 0; border: 0; border-top: 1px solid #eee;">
                <p style="font-size: 0.8rem; color: #666;">
                    ${provider.meta.notes}
                </p>
            </div>
        `;

        marker.bindPopup(popupContent);
        markersCluster.addLayer(marker);
    });
}

// Event Listeners für Radio Buttons (Kategorien)
document.querySelectorAll('input[name="category"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
        renderMarkers(e.target.value);
    });
});

// NEU: Event Listener für die Verifizierungs-Checkbox
document.getElementById('filter-verified').addEventListener('change', () => {
    // Wir holen uns die aktuell ausgewählte Kategorie, damit beide Filter zusammenarbeiten
    const currentCategory = document.querySelector('input[name="category"]:checked').value;
    renderMarkers(currentCategory);
});

// Filter Event Listener
document.querySelectorAll('input[name="category"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
        renderMarkers(e.target.value);
    });
});