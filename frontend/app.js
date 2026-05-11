// Initialize map centered on the DACH region (Germany, Austria, Switzerland)
const map = L.map('map').setView([51.1657, 10.4515], 6);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 19
}).addTo(map);

// Utilize MarkerClusterGroup for scalable node rendering instead of standard LayerGroup
const markersCluster = L.markerClusterGroup({
    chunkedLoading: true,
    spiderfyOnMaxZoom: true
});
map.addLayer(markersCluster);

let allProviders = [];

// Define geo-coordinates for metropolitan areas (Fly-To navigation)
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

// Event listener for dynamic map navigation
document.getElementById('city-dropdown').addEventListener('change', (e) => {
    const city = e.target.value;
    const coords = cityCoordinates[city];
    if (coords) {
        // Execute Leaflet's smooth Fly-To animation
        map.flyTo([coords.lat, coords.lng], coords.zoom, {
            animate: true,
            duration: 1.5
        });
    }
});

// Fetch external dataset
fetch('../data/data.json')
    .then(response => response.json())
    .then(data => {
        allProviders = data;
        renderMarkers('all');
    })
    .catch(error => console.error('Error loading data:', error));

function renderMarkers(filterCategory) {
    markersCluster.clearLayers();

    // STRICT FILTER: Restrict dataset to explicitly AI-verified nodes
    let filteredData = allProviders.filter(provider => 
        provider.meta.verification_status === "ai_verified"
    );

    // Apply secondary category filter (All, DEXA, or Blood Lab)
    if (filterCategory !== 'all') {
        filteredData = filteredData.filter(provider => provider.categories.includes(filterCategory));
    }

    document.getElementById('provider-count').innerText = filteredData.length;

    filteredData.forEach(provider => {
        if (!provider.coordinates.lat) return;

        const marker = L.marker([provider.coordinates.lat, provider.coordinates.lng]);
        
        // Construct Popup Content (Verification badge omitted as dataset is strictly pre-verified)
        const popupContent = `
            <div class="custom-popup">
                <h3>${provider.name}</h3>
                <p><strong>Address:</strong> ${provider.address.full_address}</p>
                <p>🌐 <a href="${provider.contact.website}" target="_blank">Visit Website</a></p>
                <hr>
                <p style="font-size: 0.8rem; color: #666;">AI Confidence: ${(provider.meta.ai_confidence_score * 100).toFixed(1)}%</p>
            </div>
        `;

        marker.bindPopup(popupContent);
        markersCluster.addLayer(marker);
    });
}

// Event listeners for category selection
document.querySelectorAll('input[name="category"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
        renderMarkers(e.target.value);
    });
});