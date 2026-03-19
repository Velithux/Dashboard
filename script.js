// Professional $PICSOU Dashboard Script
// Enhanced with charts, better error handling, Etherscan fallback (add your API key)

const CONTRACT_ADDRESS = '0x7058f1870D2cD5C34C72d20aD0965c75C14897e5';
const ABI = [{"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"},{"internalType":"string","name":"reason","type":"string"}],"name":"aiExecuteBurn","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"newPrice","type":"uint256"},{"internalType":"string","name":"reason","type":"string"}],"name":"aiProposePrice","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bool","name":"activate","type":"bool"},{"internalType":"string","name":"reason","type":"string"}],"name":"aiToggleYield","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"index","type":"uint256"}],"name":"getAIDecision","outputs":[{"components":[{"internalType":"uint256","name":"timestamp","type":"uint256"},{"internalType":"string","name":"actionType","type":"string"},{"internalType":"string","name":"reason","type":"string"},{"internalType":"uint256","name":"value","type":"uint256"},{"internalType":"bool","name":"executed","type":"bool"}],"internalType":"struct TokenPicsou.AIDecision","name":"","type":"tuple"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getAIDecisionCount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getLastAIActionTimestamp","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getTokenPriceUSD","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getTreasuryFeeBalance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"burnThreshold","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"circulatingSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getTotalBurned","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}];
const SEPOLIA_RPC = 'https://ethereum-sepolia-rpc.publicnode.com';
const ESCAN_BASE = 'https://sepolia.etherscan.io/tx/';
const ETHERSCAN_API_KEY = 'YOUR_ETHERSCAN_API_KEY_HERE'; // Replace with your key for better tx data, optional

let provider, contract, chart;

function formatDate(timestamp) {
    return new Date(Number(timestamp) * 1000).toLocaleString();
}

function shortenHash(hash) {
    return `${hash.slice(0,6)}...${hash.slice(-4)}`;
}

function getAge(timestamp) {
    const now = Date.now() / 1000;
    const diff = now - timestamp;
    const mins = Math.floor(diff / 60);
    const hours = Math.floor(mins / 60);
    const days = Math.floor(hours / 24);
    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    return `${mins}m ago`;
}

function hideError() {
    document.getElementById('errorBanner').classList.remove('show');
}

function showError(msg) {
    const banner = document.getElementById('errorBanner');
    banner.textContent = msg;
    banner.classList.add('show');
}

async function init() {
    try {
        provider = new ethers.JsonRpcProvider(SEPOLIA_RPC);
        contract = new ethers.Contract(CONTRACT_ADDRESS, ABI, provider);
        loadTheme();
        await updateDashboard();
        setInterval(updateDashboard, 10000);
    } catch (error) {
        console.error('Init error:', error);
        showError('Failed to connect to Sepolia: ' + error.message);
    }
}

function loadTheme() {
    const theme = localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.body.dataset.theme = theme;
}

function toggleTheme() {
    const current = document.body.dataset.theme;
    const next = current === 'dark' ? 'light' : 'dark';
    document.body.dataset.theme = next;
    localStorage.setItem('theme', next);
}

async function updateDashboard() {
    hideError();
    try {
        const statsGrid = document.getElementById('statsGrid');
        statsGrid.innerHTML = '<div class="loading card" style="grid-column: 1/-1;"><div class="spinner"></div>Loading stats...</div>';

        const [priceUSD, treasuryPICSOU, circ, burned, count, lastAction, threshold] = await Promise.all([
            contract.getTokenPriceUSD().then(price => Number(price) / 1e18),
            contract.getTreasuryFeeBalance().then(t => ethers.formatUnits(t, 18)),
            contract.circulatingSupply().then(c => Number(c) / 1e18),
            contract.getTotalBurned().then(b => Number(b) / 1e18),
            contract.getAIDecisionCount(),
            contract.getLastAIActionTimestamp().then(formatDate),
            contract.burnThreshold().then(t => Number(t) / 1e18)
        ]);

        statsGrid.innerHTML = `
            <div class="card">
                <div class="stat-value">\$${priceUSD.toFixed(6)}</div>
                <div class="stat-label">Price (USD)</div>
            </div>
            <div class="card">
                <div class="stat-value">${treasuryPICSOU}</div>
                <div class="stat-label">Treasury (PICSOU)</div>
            </div>
            <div class="card">
                <div class="stat-value">${circ.toLocaleString()}</div>
                <div class="stat-label">Circ. Supply</div>
            </div>
            <div class="card">
                <div class="stat-value">${burned.toLocaleString()}</div>
                <div class="stat-label">Total Burned</div>
            </div>
            <div class="card">
                <div class="stat-value">${count}</div>
                <div class="stat-label">AI Decisions</div>
            </div>
            <div class="card">
                <div class="stat-value">${lastAction}</div>
                <div class="stat-label">Last AI Action</div>
            </div>
            <div class="card">
                <div class="stat-value">${threshold.toLocaleString()}</div>
                <div class="stat-label">Burn Threshold</div>
            </div>
        `;
        updateDecisions();
        updateTransactions();
        updateChart([circ, burned]); // Simple supply/burn chart
    } catch (error) {
        console.error('Dashboard update error:', error);
        showError('Failed to update: ' + error.message);
    }
}

async function updateDecisions() {
    const list = document.getElementById('decisionsList');
    list.innerHTML = '<div class="loading"><div class="spinner"></div>Loading decisions...</div>';
    try {
        const count = await contract.getAIDecisionCount();
        const decisions = [];
        for (let i = Number(count) - 1; i >= 0 && decisions.length < 10; i--) {
            const dec = await contract.getAIDecision(i);
            if (dec.executed) {
                decisions.push({
                    action: dec.actionType,
                    reason: dec.reason,
                    value: ethers.formatUnits(dec.value, 18),
                    timestamp: formatDate(dec.timestamp)
                });
            }
        }
        list.innerHTML = decisions.length ? decisions.map(d => {
            const badgeClass = d.action.toLowerCase().includes('burn') ? 'badge-burn' : d.action.includes('price') ? 'badge-price' : 'badge-yield';
            return `
                <div class="list-item">
                    <span class="badge ${badgeClass}">${d.action}</span>
                    <div class="reason">${d.reason}</div>
                    <div><strong>Value:</strong> ${parseFloat(d.value).toLocaleString()} PICSOU</div>
                    <div class="timestamp">${d.timestamp}</div>
                </div>
            `;
        }).join('') : '<div class="loading">No AI decisions yet.</div>';
    } catch (error) {
        list.innerHTML = `<div style="color: var(--error-text);">Failed to load decisions: ${error.message}</div>`;
    }
}

async function updateTransactions() {
    const list = document.getElementById('txList');
    list.innerHTML = '<div class="loading"><div class="spinner"></div>Loading tx...</div>';

    const apiKey = ETHERSCAN_API_KEY === 'YOUR_ETHERSCAN_API_KEY_HERE' ? '' : ETHERSCAN_API_KEY;
    const url = `https://api-sepolia.etherscan.io/api?module=account&action=txlist&address=${CONTRACT_ADDRESS}&startblock=0&endblock=99999999&page=1&offset=10&sort=desc&apikey=${apiKey}`;

    try {
        const response = await fetch(url);
        const data = await response.json();

        if (data.status === '1' && data.result && data.result.length > 0) {
            const txs = data.result.slice(0, 10).map(tx => ({
                hash: shortenHash(tx.hash),
                from: shortenHash(tx.from),
                age: getAge(parseInt(tx.timeStamp)),
                value: parseFloat(ethers.formatEther(tx.value)).toFixed(4),
                link: `${ESCAN_BASE}${tx.hash}`
            }));
            list.innerHTML = txs.map(tx => `
                <div class="list-item">
                    <span class="badge badge-tx">TX</span>
                    <div><strong>Hash:</strong> <a href="${tx.link}" target="_blank" class="tx-link">${tx.hash}</a></div>
                    <div class="from"><strong>From:</strong> ${tx.from}</div>
                    <div class="age">${tx.age}</div>
                    <div class="value"><strong>Value:</strong> ${tx.value} ETH</div>
                </div>
            `).join('');
        } else {
            list.innerHTML = '<div class="loading">No transactions yet.</div>';
        }
    } catch (error) {
        console.error('Tx error:', error);
        list.innerHTML = '<div class="loading">No transactions yet.</div>';
    }
}

function updateChart(data) {
    const ctx = document.getElementById('burnChart')?.getContext('2d');
    if (ctx && !chart) {
        chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Circulating', 'Burned'],
                datasets: [{ data: data, backgroundColor: ['#00ff88', '#ff4444'] }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('themeToggle').addEventListener('click', toggleTheme);
    init();
});

