// Configuration de l'API
const API_BASE_URL = 'http://127.0.0.1:9000';

// Données des actions CAC40 avec leurs informations
const CAC40_STOCKS = {
    "Air Liquide": { symbol: "AI.PA", sector: "Industrie" },
    "Airbus": { symbol: "AIR.PA", sector: "Industrie" },
    "ArcelorMittal": { symbol: "MT.AS", sector: "Industrie" },
    "AXA": { symbol: "CS.PA", sector: "Assurance" },
    "BNP Paribas": { symbol: "BNP.PA", sector: "Banque" },
    "Bouygues": { symbol: "EN.PA", sector: "Construction" },
    "Capgemini": { symbol: "CAP.PA", sector: "Technologie" },
    "Carrefour": { symbol: "CA.PA", sector: "Distribution" },
    "Crédit Agricole": { symbol: "ACA.PA", sector: "Banque" },
    "Danone": { symbol: "BN.PA", sector: "Consommation" },
    "Dassault Systèmes": { symbol: "DSY.PA", sector: "Technologie" },
    "Engie": { symbol: "ENGI.PA", sector: "Énergie" },
    "EssilorLuxottica": { symbol: "EL.PA", sector: "Santé" },
    "Eurofins Scientific": { symbol: "ERF.PA", sector: "Santé" },
    "Hermès": { symbol: "RMS.PA", sector: "Luxe" },
    "Kering": { symbol: "KER.PA", sector: "Luxe" },
    "Legrand": { symbol: "LR.PA", sector: "Industrie" },
    "L'Oréal": { symbol: "OR.PA", sector: "Consommation" },
    "LVMH": { symbol: "MC.PA", sector: "Luxe" },
    "Michelin": { symbol: "ML.PA", sector: "Industrie" },
    "Orange": { symbol: "ORA.PA", sector: "Technologie" },
    "Pernod Ricard": { symbol: "RI.PA", sector: "Consommation" },
    "Renault": { symbol: "RNO.PA", sector: "Automobile" },
    "Safran": { symbol: "SAF.PA", sector: "Industrie" },
    "Saint-Gobain": { symbol: "SGO.PA", sector: "Industrie" },
    "Sanofi": { symbol: "SAN.PA", sector: "Santé" },
    "Schneider Electric": { symbol: "SU.PA", sector: "Industrie" },
    "Société Générale": { symbol: "GLE.PA", sector: "Banque" },
    "STMicroelectronics": { symbol: "STM.PA", sector: "Technologie" },
    "Teleperformance": { symbol: "TEP.PA", sector: "Services" },
    "Thales": { symbol: "HO.PA", sector: "Défense" },
    "TotalEnergies": { symbol: "TTE.PA", sector: "Énergie" },
    "Unibail-Rodamco-Westfield": { symbol: "URW.AS", sector: "Immobilier" },
    "Veolia": { symbol: "VIE.PA", sector: "Services" },
    "Vinci": { symbol: "DG.PA", sector: "Construction" },
    "Vivendi": { symbol: "VIV.PA", sector: "Médias" }
};

// Variables globales
let fakeData = {};
let filteredStocks = Object.keys(CAC40_STOCKS);
let allStocksData = {};
let priceChart = null;
let currentStockName = null;
let sentimentData = {};
let articlesData = {};
let currentArticleUrls = {
    positive: null,
    negative: null,
    random: null
};

// Éléments DOM
const searchInput = document.getElementById('searchInput');
const sectorFilter = document.getElementById('sectorFilter');
const performanceFilter = document.getElementById('performanceFilter');
const historyDays = document.getElementById('historyDays');
const applyFiltersBtn = document.getElementById('applyFilters');
const loadingIndicator = document.getElementById('loadingIndicator');
const stocksGrid = document.getElementById('stocksGrid');
const stockModal = document.getElementById('stockModal');
const closeModalBtn = document.getElementById('closeModal');

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
    setDefaultDates();
});

function initializeApp() {
    loadFakeData();
    loadAllStocksData();
    populateSectorFilter();
}

function setupEventListeners() {
    // Filtrage réactif
    searchInput.addEventListener('input', handleSearch);
    sectorFilter.addEventListener('change', applyFilters);
    performanceFilter.addEventListener('change', applyFilters);
    
    // Bouton reset
    document.getElementById('resetFilters').addEventListener('click', resetFilters);
    
    closeModalBtn.addEventListener('click', closeModal);
    
    // Recharger les données quand la période change
    historyDays.addEventListener('change', function() {
        loadAllStocksData();
        // Recharger aussi les sparklines avec les nouvelles données
        reloadAllSparklines();
    });
    
    // Les event listeners pour les articles seront ajoutés dynamiquement lors de l'affichage des articles
    
    
    // Fermer le modal en cliquant à l'extérieur
    stockModal.addEventListener('click', function(e) {
        if (e.target === stockModal) {
            closeModal();
        }
    });
}

function setDefaultDates() {
    // Plus besoin de définir des dates par défaut
    // Les dernières valeurs sont chargées automatiquement
}

async function loadFakeData() {
    try {
        const response = await fetch('fake_data.json');
        fakeData = await response.json();
    } catch (error) {
        console.error('Erreur lors du chargement des données fake:', error);
        // Données par défaut si le fichier n'est pas trouvé
        fakeData = generateDefaultFakeData();
    }
    
    // Charger les données de sentiment
    try {
        const response = await fetch('articles_epures_groupes.json');
        const sentimentArray = await response.json();
        sentimentData = {};
        sentimentArray.forEach(item => {
            if (!sentimentData[item.ticker]) {
                sentimentData[item.ticker] = {};
            }
            sentimentData[item.ticker][item.published_date] = {
                sentiment: item.sentiment_score_mean,
                nb_articles: item.nb_articles
            };
        });
        console.log('Données de sentiment chargées:', sentimentData);
    } catch (error) {
        console.error('Erreur lors du chargement des données de sentiment:', error);
        sentimentData = {};
    }
    
    // Charger les données d'articles
    try {
        const response = await fetch('synthese_cac40_mensuelle.json');
        const articlesArray = await response.json();
        articlesData = {};
        articlesArray.forEach(item => {
            articlesData[item.ticker] = item;
        });
        console.log('Données d\'articles chargées:', articlesData);
    } catch (error) {
        console.error('Erreur lors du chargement des données d\'articles:', error);
        articlesData = {};
    }
}

async function loadAllStocksData(periodDays = null) {
    showLoading();
    try {
        // Utiliser la période sélectionnée ou 2 jours par défaut
        const days = periodDays || historyDays.value;
        const response = await fetch(`${API_BASE_URL}/get_latest_cac40_prices?period_days=${days}`);
        
        if (!response.ok) {
            throw new Error(`Erreur HTTP: ${response.status}`);
        }
        
        allStocksData = await response.json();
        console.log('Dernières valeurs CAC40 chargées:', allStocksData);
        
        // Afficher les stocks avec les vraies données
        displayStocks();
        
    } catch (error) {
        console.error('Erreur lors du chargement des dernières valeurs CAC40:', error);
        // Fallback sur l'affichage basique
        displayStocks();
    } finally {
        hideLoading();
    }
}

function generateDefaultFakeData() {
    const defaultData = {};
    Object.keys(CAC40_STOCKS).forEach(stock => {
        defaultData[stock] = {
            confidence: Math.floor(Math.random() * 40) + 60,
            confidence_description: "Analyse en cours...",
            current_price: Math.random() * 500 + 50,
            projected_price: 0,
            projection_change: Math.random() * 20 - 10,
            projection_description: "Projection basée sur l'analyse technique et fondamentale.",
            keywords: ["analyse", "technique", "fondamentale", "marché"],
            sector: CAC40_STOCKS[stock].sector,
            performance: Math.random() > 0.5 ? "positive" : "negative"
        };
        defaultData[stock].projected_price = defaultData[stock].current_price * (1 + defaultData[stock].projection_change / 100);
    });
    return defaultData;
}

function populateSectorFilter() {
    const sectors = [...new Set(Object.values(CAC40_STOCKS).map(stock => stock.sector))];
    sectors.forEach(sector => {
        const option = document.createElement('option');
        option.value = sector;
        option.textContent = sector;
        sectorFilter.appendChild(option);
    });
}

function handleSearch() {
    const searchTerm = searchInput.value.toLowerCase();
    filteredStocks = Object.keys(CAC40_STOCKS).filter(stock => 
        stock.toLowerCase().includes(searchTerm) ||
        CAC40_STOCKS[stock].symbol.toLowerCase().includes(searchTerm)
    );
    applyFilters();
}

function applyFilters() {
    showLoading();
    
    setTimeout(() => {
        let filtered = [...filteredStocks];
        
        // Filtre par secteur
        const selectedSector = sectorFilter.value;
        if (selectedSector) {
            filtered = filtered.filter(stock => 
                CAC40_STOCKS[stock].sector === selectedSector
            );
        }
        
        // Filtre par performance (utilise les données calculées par l'API)
        const selectedPerformance = performanceFilter.value;
        if (selectedPerformance) {
            filtered = filtered.filter(stock => {
                // Utiliser la performance calculée par l'API (comparaison début vs fin de période)
                if (allStocksData.stocks && allStocksData.stocks[stock]) {
                    const stockData = allStocksData.stocks[stock];
                    const performance = stockData.price_change;
                    
                    if (performance !== undefined) {
                        if (selectedPerformance === 'positive') {
                            return performance > 0;
                        } else if (selectedPerformance === 'negative') {
                            return performance < 0;
                        } else if (selectedPerformance === 'stable') {
                            return Math.abs(performance) < 1; // Moins de 1% de variation
                        }
                    }
                }
                return true;
            });
        }
        
        displayStocks(filtered);
        hideLoading();
    }, 500);
}

async function displayStocks(stocksToShow = filteredStocks) {
    stocksGrid.innerHTML = '';
    
    // Afficher les cartes avec les données réelles si disponibles
    stocksToShow.forEach(stock => {
        const stockCard = createStockCard(stock);
        stocksGrid.appendChild(stockCard);
    });
}

function createStockCard(stockName) {
    const stock = CAC40_STOCKS[stockName];
    const fakeStockData = fakeData[stockName];
    const realStockData = allStocksData.stocks ? allStocksData.stocks[stockName] : null;
    
    const card = document.createElement('div');
    card.className = 'stock-card';
    card.dataset.stockName = stockName;
    card.onclick = () => openStockDetail(stockName);
    
    // Utiliser les données réelles si disponibles
    let currentPrice = '--';
    let change = 0;
    let changeClass = 'neutral';
    
    if (realStockData && realStockData.last_price) {
        currentPrice = realStockData.last_price.toFixed(2);
        
        // Utiliser la performance calculée par l'API (comparaison début vs fin de période)
        change = realStockData.price_change || 0;
        changeClass = change > 0 ? 'positive' : change < 0 ? 'negative' : 'neutral';
    } else if (fakeStockData) {
        // Fallback sur les données fake
        currentPrice = fakeStockData.current_price.toFixed(2);
        change = fakeStockData.projection_change;
        changeClass = change > 0 ? 'positive' : change < 0 ? 'negative' : 'neutral';
    }
    
    card.innerHTML = `
        <div class="stock-header">
            <div class="stock-name">${stockName}</div>
            <div class="stock-symbol">${stock.symbol}</div>
        </div>
        <div class="stock-price">${currentPrice} €</div>
        <div class="stock-change ${changeClass}">
            <i class="fas fa-arrow-${change > 0 ? 'up' : 'down'}"></i>
            ${change.toFixed(2)}%
        </div>
        <div class="stock-sparkline">
            <canvas class="sparkline-chart" width="200" height="60"></canvas>
        </div>
        <div class="stock-info">
            <p><strong>Secteur:</strong> ${stock.sector}</p>
        </div>
    `;
    
    // Créer la sparkline après l'ajout au DOM
    setTimeout(async () => {
        await createSparkline(card, stockName);
    }, 100);
    
    return card;
}

async function openStockDetail(stockName) {
    currentStockName = stockName;
    showLoading();
    
    try {
        // Charger l'historique détaillé (30 derniers jours)
        const historyData = await fetchStockHistory(stockName);
        
        // Préparer les données pour l'affichage
        const stockInfo = CAC40_STOCKS[stockName];
        const fakeInfo = fakeData[stockName] || {};
        const latestData = allStocksData.stocks ? allStocksData.stocks[stockName] : null;
        
        // Mettre à jour le modal avec les données d'historique
        updateModalContent(stockName, stockInfo, fakeInfo, historyData, latestData);
        
        // Afficher le modal
        stockModal.classList.remove('hidden');
        
    } catch (error) {
        console.error('Erreur lors du chargement des détails:', error);
        alert('Erreur lors du chargement des données de l\'action');
    } finally {
        hideLoading();
    }
}

async function fetchStockHistory(stockName, days = null) {
    try {
        // Utiliser la valeur du select si pas de paramètre
        const daysToFetch = days || historyDays.value;
        
        const response = await fetch(
            `${API_BASE_URL}/get_stock_history?stock=${encodeURIComponent(stockName)}&days=${daysToFetch}`
        );
        
        if (!response.ok) {
            throw new Error(`Erreur HTTP: ${response.status}`);
        }
        
        // Récupérer directement le JSON depuis l'API
        const data = await response.json();
        
        return data;
        
    } catch (error) {
        console.error('Erreur API:', error);
        throw error; // Propager l'erreur pour la gestion en amont
    }
}

// Fonction de fallback pour compatibilité (plus utilisée)
async function fetchStockData(stockName) {
    // Cette fonction n'est plus utilisée avec la nouvelle architecture
    // Elle est gardée pour compatibilité
    return await fetchStockHistory(stockName);
}


async function updateModalContent(stockName, stockInfo, fakeInfo, historyData, latestData) {
    // Titre
    document.getElementById('modalTitle').textContent = `${stockName} (${stockInfo.symbol})`;
    
    // Charger et afficher les données de corrélation depuis l'API
    try {
        const correlationData = await fetchCorrelationData(stockName);
        
        if (correlationData && correlationData.correlation) {
            const correlation = correlationData.correlation.mean_correlation;
            
            // Mettre à jour la jauge de corrélation
            updateCorrelationGauge(correlation);
            
            let correlationDescription = '';
            if (correlation > 0.3) {
                correlationDescription = 'Corrélation positive modérée avec les indicateurs du marché. Données fiables.';
            } else if (correlation > 0.1) {
                correlationDescription = 'Corrélation légèrement positive. Données généralement utilisables.';
            } else if (correlation > -0.1) {
                correlationDescription = 'Corrélation neutre. Données moyennement fiables pour l\'analyse.';
            } else if (correlation > -0.3) {
                correlationDescription = 'Corrélation légèrement négative. Prudence recommandée.';
            } else {
                correlationDescription = 'Corrélation négative. Signaux probablement inversés.';
            }
            document.getElementById('correlationDescription').textContent = correlationDescription;
        } else {
            // Fallback vers les données fake
            const correlation = fakeInfo.correlation || 0.75;
            updateCorrelationGauge(correlation);
            document.getElementById('correlationDescription').textContent = 'Données de corrélation non disponibles.';
        }
    } catch (error) {
        console.error('Erreur lors du chargement des données de corrélation:', error);
        // Fallback vers les données fake
        const correlation = fakeInfo.correlation || 0.75;
        updateCorrelationGauge(correlation);
        document.getElementById('correlationDescription').textContent = 'Erreur de chargement des données de corrélation.';
    }
    
    // Charger et afficher les articles depuis l'API
    try {
        const articlesData = await fetchArticlesData(stockName);
        
        if (articlesData && articlesData.articles) {
            // Article le plus positif
            const positiveArticle = articlesData.articles.positive;
            document.getElementById('positiveArticleTitle').textContent = positiveArticle.title || 'Aucun article positif disponible';
            currentArticleUrls.positive = positiveArticle.url || null;
            const positiveDesc = document.getElementById('positiveArticleDesc');
            if (positiveArticle.description && positiveArticle.description.trim() !== '') {
                positiveDesc.textContent = positiveArticle.description;
                positiveDesc.style.display = 'block';
            } else {
                positiveDesc.style.display = 'none';
            }
            
            // Ajouter l'event listener pour l'article positif
            const positiveArticleElement = document.getElementById('positiveArticle');
            if (positiveArticleElement) {
                positiveArticleElement.onclick = function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    if (currentArticleUrls.positive) {
                        window.open(currentArticleUrls.positive, '_blank');
                    }
                };
            }
            
            // Article le plus négatif
            const negativeArticle = articlesData.articles.negative;
            document.getElementById('negativeArticleTitle').textContent = negativeArticle.title || 'Aucun article négatif disponible';
            currentArticleUrls.negative = negativeArticle.url || null;
            const negativeDesc = document.getElementById('negativeArticleDesc');
            if (negativeArticle.description && negativeArticle.description.trim() !== '') {
                negativeDesc.textContent = negativeArticle.description;
                negativeDesc.style.display = 'block';
            } else {
                negativeDesc.style.display = 'none';
            }
            
            // Ajouter l'event listener pour l'article négatif
            const negativeArticleElement = document.getElementById('negativeArticle');
            if (negativeArticleElement) {
                negativeArticleElement.onclick = function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    if (currentArticleUrls.negative) {
                        window.open(currentArticleUrls.negative, '_blank');
                    }
                };
            }
            
            // Article aléatoire
            const randomArticle = articlesData.articles.random;
            document.getElementById('randomArticleTitle').textContent = randomArticle.title || 'Aucun article aléatoire disponible';
            currentArticleUrls.random = randomArticle.url || null;
            const randomDesc = document.getElementById('randomArticleDesc');
            if (randomArticle.description && randomArticle.description.trim() !== '') {
                randomDesc.textContent = randomArticle.description;
                randomDesc.style.display = 'block';
            } else {
                randomDesc.style.display = 'none';
            }
            
            // Ajouter l'event listener pour l'article aléatoire
            const randomArticleElement = document.getElementById('randomArticle');
            if (randomArticleElement) {
                randomArticleElement.onclick = function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    if (currentArticleUrls.random) {
                        window.open(currentArticleUrls.random, '_blank');
                    }
                };
            }
            
            // Mettre à jour les mots-clés avec les vraies données
            const keywordsContainer = document.getElementById('keywordsList');
            keywordsContainer.innerHTML = '';
            
            const keywords = articlesData.keywords || [];
            keywords.slice(0, 10).forEach(keyword => { // Limiter à 10 mots-clés
                const tag = document.createElement('span');
                tag.className = 'keyword-tag';
                tag.textContent = keyword;
                keywordsContainer.appendChild(tag);
            });
        } else {
            // Fallback si pas de données d'articles
            document.getElementById('positiveArticleTitle').textContent = 'Aucun article disponible';
            document.getElementById('positiveArticleDesc').textContent = 'Données d\'articles non disponibles pour cette action';
            document.getElementById('negativeArticleTitle').textContent = 'Aucun article disponible';
            document.getElementById('negativeArticleDesc').textContent = 'Données d\'articles non disponibles pour cette action';
            document.getElementById('randomArticleTitle').textContent = 'Aucun article disponible';
            document.getElementById('randomArticleDesc').textContent = 'Données d\'articles non disponibles pour cette action';
            currentArticleUrls.positive = null;
            currentArticleUrls.negative = null;
            currentArticleUrls.random = null;
        }
    } catch (error) {
        console.error('Erreur lors du chargement des articles:', error);
        // Fallback si erreur
        document.getElementById('positiveArticleTitle').textContent = 'Erreur de chargement';
        document.getElementById('positiveArticleDesc').textContent = 'Impossible de charger les articles';
        document.getElementById('negativeArticleTitle').textContent = 'Erreur de chargement';
        document.getElementById('negativeArticleDesc').textContent = 'Impossible de charger les articles';
        document.getElementById('randomArticleTitle').textContent = 'Erreur de chargement';
        document.getElementById('randomArticleDesc').textContent = 'Impossible de charger les articles';
    }
    
    // Graphique avec données d'historique
    await updateChart(historyData.open_prices);
    
    // Mettre à jour l'indicateur de sentiment
    await updateSentimentIndicator(historyData.open_prices);
}

async function updateChart(priceData) {
    const canvas = document.getElementById('priceChart');
    const ctx = canvas.getContext('2d');
    
    // Détruire le graphique précédent s'il existe
    if (priceChart) {
        priceChart.destroy();
    }
    
    if (priceData && priceData.length > 0) {
        // Préparer les données pour Chart.js
        const labels = priceData.map(item => {
            const date = new Date(item.date);
            return date.toLocaleDateString('fr-FR', { month: 'short', day: 'numeric' });
        });
        
        const prices = priceData.map(item => item.open_price);
        
        // Générer des données de sentiment (vraies avec fallback)
        const sentiments = await generateSentimentData(priceData.length, priceData, currentStockName);
        
        // Charger les vraies projections depuis l'API
        let predictionData = [];
        let predictionLabels = [];
        try {
            const correlationData = await fetchCorrelationData(currentStockName);
            if (correlationData && correlationData.forecast && correlationData.forecast.length > 0) {
                // Utiliser les vraies projections
                predictionData = correlationData.forecast.map(forecast => forecast.predicted_price);
                predictionLabels = correlationData.forecast.map(forecast => `+${forecast.horizon}j`);
            } else {
                // Fallback vers les données fictives
                predictionData = generatePredictionData(prices);
                predictionLabels = generatePredictionLabels(labels, 7);
            }
        } catch (error) {
            console.error('Erreur lors du chargement des projections:', error);
            // Fallback vers les données fictives
            predictionData = generatePredictionData(prices);
            predictionLabels = generatePredictionLabels(labels, 7);
        }
        
        // Calculer les valeurs min et max incluant les projections
        const allPrices = [...prices, ...predictionData];
        const minPrice = Math.min(...allPrices);
        const maxPrice = Math.max(...allPrices);
        const priceRange = maxPrice - minPrice;
        
        // Ajouter une marge de 5% pour une meilleure visibilité
        const margin = priceRange * 0.05;
        const chartMin = minPrice - margin;
        const chartMax = maxPrice + margin;
        
        // Couleur du graphique basée sur la tendance
        const firstPrice = prices[0];
        const lastPrice = prices[prices.length - 1];
        const isPositive = lastPrice >= firstPrice;
        const priceColor = isPositive ? '#27ae60' : '#e74c3c';
        
        // Calculer l'échelle du sentiment basée sur min/max de l'action
        // -1 de sentiment = minPrice, +1 de sentiment = maxPrice
        const sentimentScale = (maxPrice - minPrice) / 2; // Demi-amplitude de l'échelle des prix
        const sentimentOffset = minPrice + sentimentScale; // Centre de l'échelle (moyenne min/max)
        
        priceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [...labels, ...predictionLabels],
                datasets: [
                    {
                        label: 'Prix d\'ouverture (€)',
                        data: [...prices, ...new Array(7).fill(null)], // Prix historiques + prédictions vides
                        borderColor: priceColor,
                        backgroundColor: priceColor + '20',
                        borderWidth: 3,
                        fill: false,
                        tension: 0.4,
                        pointBackgroundColor: priceColor,
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Prédiction (€)',
                        data: [...new Array(prices.length).fill(null), ...predictionData], // Historique vide + prédictions
                        borderColor: '#ff6b6b',
                        backgroundColor: '#ff6b6b' + '20',
                        borderWidth: 3,
                        borderDash: [5, 5],
                        fill: false,
                        tension: 0.4,
                        pointBackgroundColor: '#ff6b6b',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointRadius: 3,
                        pointHoverRadius: 5,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Sentiment',
                        data: sentiments.map(s => sentimentOffset + (s * sentimentScale)),
                        borderColor: '#4ecdc4',
                        backgroundColor: '#4ecdc4' + '20',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.3,
                        pointBackgroundColor: '#4ecdc4',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 1,
                        pointRadius: 2,
                        pointHoverRadius: 4,
                        yAxisID: 'y',
                        hidden: false // Visible par défaut
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            padding: 20,
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                const datasetLabel = context.dataset.label;
                                const value = context.parsed.y;
                                
                                if (datasetLabel === 'Sentiment') {
                                    const sentimentValue = sentiments[context.dataIndex];
                                    return `${datasetLabel}: ${sentimentValue.toFixed(2)}`;
                                } else {
                                    return `${datasetLabel}: ${value.toFixed(2)} €`;
                                }
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        grid: {
                            display: false
                        },
                        ticks: {
                            maxTicksLimit: 10,
                            callback: function(value, index) {
                                // Afficher seulement certaines dates pour éviter l'encombrement
                                return index % Math.ceil(labels.length / 8) === 0 ? this.getLabelForValue(value) : '';
                            }
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        min: chartMin,
                        max: chartMax,
                        grid: {
                            color: '#f3f4f6',
                            drawBorder: false
                        },
                        ticks: {
                            callback: function(value) {
                                return value.toFixed(2) + ' €';
                            }
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: false, // Masqué par défaut
                        position: 'right',
                        grid: {
                            drawOnChartArea: false,
                        },
                        ticks: {
                            callback: function(value) {
                                return value.toFixed(2);
                            }
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                elements: {
                    point: {
                        hoverRadius: 8
                    }
                }
            }
        });
    } else {
        // Afficher un message d'erreur si pas de données
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#7f8c8d';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Aucune donnée disponible', canvas.width / 2, canvas.height / 2);
    }
}

async function generateSentimentData(length, priceData, stockName) {
    // Utiliser l'API pour récupérer les vrais sentiments
    if (!stockName || !priceData || priceData.length === 0) {
        // Fallback vers l'ancienne génération fictive
        const sentiments = [];
        let currentSentiment = (Math.random() - 0.5) * 0.4;
        
        for (let i = 0; i < length; i++) {
            const volatility = (Math.random() - 0.5) * 0.3;
            currentSentiment += volatility;
            currentSentiment = Math.max(-1, Math.min(1, currentSentiment));
            const trend = Math.sin(i / length * Math.PI * 2) * 0.2;
            currentSentiment += trend;
            sentiments.push(Math.max(-1, Math.min(1, currentSentiment)));
        }
        return sentiments;
    }
    
    try {
        // Récupérer les données de sentiment depuis l'API
        const sentimentData = await fetchSentimentData(stockName, 30);
        
        // Créer un dictionnaire pour un accès rapide par date
        const sentimentByDate = {};
        sentimentData.forEach(item => {
            sentimentByDate[item.date] = item.sentiment;
        });
        
        // Extraire les sentiments dans l'ordre des prix
        const sentiments = [];
        for (let i = 0; i < priceData.length; i++) {
            const date = priceData[i].date;
            const sentiment = sentimentByDate[date] || 0; // Fallback à 0 si pas trouvé
            sentiments.push(sentiment);
        }
        
        return sentiments;
    } catch (error) {
        console.error('Erreur lors de la récupération des sentiments, utilisation de données fictives:', error);
        
        // Fallback vers des données fictives
        const sentiments = [];
        let currentSentiment = (Math.random() - 0.5) * 0.4;
        
        for (let i = 0; i < length; i++) {
            const volatility = (Math.random() - 0.5) * 0.3;
            currentSentiment += volatility;
            currentSentiment = Math.max(-1, Math.min(1, currentSentiment));
            const trend = Math.sin(i / length * Math.PI * 2) * 0.2;
            currentSentiment += trend;
            sentiments.push(Math.max(-1, Math.min(1, currentSentiment)));
        }
        return sentiments;
    }
}

function generatePredictionData(historicalPrices) {
    // Générer des prédictions basées sur la tendance historique
    const predictions = [];
    const lastPrice = historicalPrices[historicalPrices.length - 1];
    const secondLastPrice = historicalPrices[historicalPrices.length - 2];
    
    // Calculer la tendance
    const trend = (lastPrice - secondLastPrice) / secondLastPrice;
    
    // Générer 7 prédictions
    for (let i = 1; i <= 7; i++) {
        // Appliquer la tendance avec de la volatilité
        const volatility = (Math.random() - 0.5) * 0.02; // ±1% de volatilité
        const predictedPrice = lastPrice * Math.pow(1 + trend + volatility, i);
        
        predictions.push(predictedPrice);
    }
    
    return predictions;
}

function generatePredictionLabels(historicalLabels, predictionDays) {
    const predictionLabels = [];
    const lastDate = new Date(historicalLabels[historicalLabels.length - 1]);
    
    for (let i = 1; i <= predictionDays; i++) {
        const futureDate = new Date(lastDate);
        futureDate.setDate(futureDate.getDate() + i);
        
        // Skip weekends
        while (futureDate.getDay() === 0 || futureDate.getDay() === 6) {
            futureDate.setDate(futureDate.getDate() + 1);
        }
        
        predictionLabels.push(futureDate.toLocaleDateString('fr-FR', { month: 'short', day: 'numeric' }));
    }
    
    return predictionLabels;
}

async function updateSentimentIndicator(priceData) {
    if (!priceData || priceData.length === 0) return;
    
    try {
        // Générer les mêmes données de sentiment que pour le graphique
        const sentiments = await generateSentimentData(priceData.length, priceData, currentStockName);
        
        // Calculer le sentiment moyen
        const avgSentiment = sentiments.reduce((a, b) => a + b, 0) / sentiments.length;
        
        // Mettre à jour seulement la barre de sentiment
        const sentimentFill = document.getElementById('sentimentFill');
        const percentage = ((avgSentiment + 1) / 2) * 100; // Convertir de [-1,1] à [0,100]
        sentimentFill.style.width = `${percentage}%`;
        
        // Changer la couleur selon le sentiment
        if (avgSentiment > 0.2) {
            sentimentFill.style.background = 'linear-gradient(90deg, #10b981 0%, #059669 100%)';
        } else if (avgSentiment < -0.2) {
            sentimentFill.style.background = 'linear-gradient(90deg, #ef4444 0%, #dc2626 100%)';
        } else {
            sentimentFill.style.background = 'linear-gradient(90deg, #f59e0b 0%, #d97706 100%)';
        }
    } catch (error) {
        console.error('Erreur lors de la mise à jour de l\'indicateur de sentiment:', error);
        // Fallback vers une valeur neutre
        const sentimentFill = document.getElementById('sentimentFill');
        sentimentFill.style.width = '50%';
        sentimentFill.style.background = 'linear-gradient(90deg, #f59e0b 0%, #d97706 100%)';
    }
}

async function createSparkline(card, stockName) {
    const canvas = card.querySelector('.sparkline-chart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    
    // Récupérer les vraies données de prix pour la période sélectionnée
    let prices = [];
    try {
        const periodDays = parseInt(document.getElementById('historyDays').value) || 30;
        const response = await fetch(`${API_BASE_URL}/get_stock_history?stock_name=${encodeURIComponent(stockName)}&days=${periodDays}`);
        
        if (response.ok) {
            const data = await response.json();
            if (data.open_prices && data.open_prices.length > 0) {
                prices = data.open_prices.map(item => item.open_price);
            }
        }
    } catch (error) {
        console.error('Erreur lors du chargement des données sparkline:', error);
    }
    
    // Fallback vers des données fictives si pas de données réelles
    if (prices.length === 0) {
        const dataPoints = 20;
        prices = generateSparklineData(dataPoints, stockName);
    }
    
    // Calculer les dimensions du graphique avec une marge pour mieux voir les variations
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const priceRange = maxPrice - minPrice || 1;
    
    // Ajouter une marge de 10% pour mieux voir les variations
    const margin = priceRange * 0.1;
    const adjustedMinPrice = minPrice - margin;
    const adjustedMaxPrice = maxPrice + margin;
    const adjustedPriceRange = adjustedMaxPrice - adjustedMinPrice;
    
    // Déterminer la couleur basée sur la performance réelle
    let sparklineColor = '#6b7280'; // Gris par défaut
    if (allStocksData.stocks && allStocksData.stocks[stockName]) {
        const stockData = allStocksData.stocks[stockName];
        const performance = stockData.price_change || 0;
        
        if (performance > 0.02) { // Plus de 2% de hausse
            sparklineColor = '#059669'; // Vert foncé
        } else if (performance > 0) { // Hausse modérée
            sparklineColor = '#10b981'; // Vert clair
        } else if (performance < -0.02) { // Plus de 2% de baisse
            sparklineColor = '#dc2626'; // Rouge foncé
        } else if (performance < 0) { // Baisse modérée
            sparklineColor = '#ef4444'; // Rouge clair
        } else {
            sparklineColor = '#6b7280'; // Gris pour neutre
        }
    } else {
        // Fallback sur la tendance des prix fictifs
        sparklineColor = prices[prices.length - 1] > prices[0] ? '#059669' : '#dc2626';
    }
    
    // Dessiner la sparkline
    ctx.clearRect(0, 0, width, height);
    ctx.strokeStyle = sparklineColor;
    ctx.lineWidth = 2;
    ctx.beginPath();
    
    prices.forEach((price, index) => {
        const x = (index / (prices.length - 1)) * width;
        const y = height - ((price - adjustedMinPrice) / adjustedPriceRange) * height;
        
        if (index === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });
    
    ctx.stroke();
    
    // Ajouter un point pour la dernière valeur
    const lastX = width;
    const lastY = height - ((prices[prices.length - 1] - minPrice) / priceRange) * height;
    ctx.fillStyle = ctx.strokeStyle;
    ctx.beginPath();
    ctx.arc(lastX, lastY, 2, 0, 2 * Math.PI);
    ctx.fill();
}

function generateSparklineData(points, stockName) {
    // Générer des données réalistes basées sur le nom de l'action
    const basePrice = 50 + (stockName.length * 5); // Prix de base variable
    const prices = [basePrice];
    
    for (let i = 1; i < points; i++) {
        const volatility = (Math.random() - 0.5) * 4; // Volatilité de ±2%
        const trend = Math.sin(i / points * Math.PI * 2) * 2; // Tendance cyclique
        const newPrice = prices[i - 1] * (1 + (volatility + trend) / 100);
        prices.push(Math.max(newPrice, basePrice * 0.8)); // Prix minimum
    }
    
    return prices;
}

// Fonction pour récupérer les données de sentiment depuis l'API
async function fetchSentimentData(stockName, days = 30) {
    try {
        const response = await fetch(`${API_BASE_URL}/get_sentiment_data?stock_name=${encodeURIComponent(stockName)}&days=${days}`);
        
        if (!response.ok) {
            throw new Error(`Erreur HTTP: ${response.status}`);
        }
        
        const data = await response.json();
        return data.sentiment_data;
    } catch (error) {
        console.error('Erreur lors de la récupération des sentiments:', error);
        return [];
    }
}

// Fonction pour récupérer les données d'articles depuis l'API
async function fetchArticlesData(stockName) {
    try {
        const response = await fetch(`${API_BASE_URL}/get_articles_data?stock_name=${encodeURIComponent(stockName)}`);
        
        if (!response.ok) {
            throw new Error(`Erreur HTTP: ${response.status}`);
        }
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Erreur lors de la récupération des articles:', error);
        return null;
    }
}

// Fonction pour récupérer les données de corrélation depuis l'API
async function fetchCorrelationData(stockName) {
    try {
        const response = await fetch(`${API_BASE_URL}/get_correlation_data?stock_name=${encodeURIComponent(stockName)}`);
        
        if (!response.ok) {
            throw new Error(`Erreur HTTP: ${response.status}`);
        }
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Erreur lors de la récupération des données de corrélation:', error);
        return null;
    }
}

// Fonction pour récupérer le sentiment avec fallback (deprecated - utilise maintenant l'API)
function getSentimentForDate(ticker, date) {
    if (!sentimentData[ticker]) {
        return 0; // Pas de données pour ce ticker
    }
    
    // Chercher la date exacte
    if (sentimentData[ticker][date]) {
        return sentimentData[ticker][date].sentiment;
    }
    
    // Chercher la veille
    const yesterday = new Date(date);
    yesterday.setDate(yesterday.getDate() - 1);
    const yesterdayStr = yesterday.toISOString().split('T')[0];
    
    if (sentimentData[ticker][yesterdayStr]) {
        return sentimentData[ticker][yesterdayStr].sentiment;
    }
    
    // Chercher dans les 7 jours précédents
    for (let i = 2; i <= 7; i++) {
        const pastDate = new Date(date);
        pastDate.setDate(pastDate.getDate() - i);
        const pastDateStr = pastDate.toISOString().split('T')[0];
        
        if (sentimentData[ticker][pastDateStr]) {
            return sentimentData[ticker][pastDateStr].sentiment;
        }
    }
    
    return 0; // Pas de données trouvées
}


function updateCorrelationGauge(correlation) {
    const gauge = document.getElementById('correlationGauge');
    if (gauge) {
        // Convertir la corrélation (-1 à 1) en position (0% à 100%)
        // Corrélation -1 = 0%, 0 = 50%, 1 = 100%
        const position = ((correlation + 1) / 2) * 100; // -1->0%, 0->50%, 1->100%
        
        gauge.style.setProperty('--gauge-position', `${position}%`);
        gauge.style.setProperty('--gauge-width', '6px'); // Largeur fixe pour l'indicateur
        gauge.setAttribute('data-value', correlation.toFixed(3));
    }
}

function resetFilters() {
    // Reset des filtres
    searchInput.value = '';
    sectorFilter.value = '';
    performanceFilter.value = '';
    
    // Réappliquer les filtres (qui va afficher tout)
    applyFilters();
}

async function reloadAllSparklines() {
    // Recharger toutes les sparklines visibles
    const cards = document.querySelectorAll('.stock-card');
    for (const card of cards) {
        const stockName = card.dataset.stockName;
        if (stockName) {
            await createSparkline(card, stockName);
        }
    }
}


function closeModal() {
    stockModal.classList.add('hidden');
    // Réinitialiser quand on ferme le modal
    currentStockName = null;
}

function showLoading() {
    loadingIndicator.classList.remove('hidden');
}

function hideLoading() {
    loadingIndicator.classList.add('hidden');
}

// Gestion des erreurs globales
window.addEventListener('error', function(e) {
    console.error('Erreur JavaScript:', e.error);
});

// Export pour utilisation dans d'autres scripts si nécessaire
window.CAC40Dashboard = {
    CAC40_STOCKS,
    openStockDetail,
    applyFilters
};
