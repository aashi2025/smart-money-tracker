// Institutional Smart Money Dashboard Controller

let activeTab = 'idxFut';
let currentParticipantMetrics = null;
let vpChartInstance = null;
let optChartInstance = null;

document.addEventListener('DOMContentLoaded', () => {
    // Set default date to today
    const todayStr = new Date().toISOString().split('T')[0];
    document.getElementById('nseDatePicker').value = todayStr;

    // Initialize Event Listeners
    initEventListeners();

    // Initial Load
    loadAllDashboardData();
});

function initEventListeners() {
    // Symbol Select Change
    document.getElementById('symbolSelect').addEventListener('change', () => {
        loadVolumeProfile();
        loadOptionChain();
        loadSummaryCards();
    });

    // Date Picker Change or Fetch Button
    document.getElementById('btnFetchNse').addEventListener('click', () => {
        loadParticipantData();
        loadSummaryCards();
    });

    // Recalc Profile Button
    document.getElementById('btnCalcVp').addEventListener('click', () => {
        loadVolumeProfile();
    });

    // Tab Switchers for Participant Table
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.tab-btn').forEach(b => {
                b.classList.remove('active', 'text-sky-400', 'border-b-2', 'border-sky-400');
                b.classList.add('text-gray-400');
            });
            e.target.classList.add('active', 'text-sky-400', 'border-b-2', 'border-sky-400');
            e.target.classList.remove('text-gray-400');
            
            activeTab = e.target.getAttribute('data-tab');
            renderParticipantTable();
        });
    });
}

function loadAllDashboardData() {
    loadSummaryCards();
    loadParticipantData();
    loadVolumeProfile();
    loadOptionChain();
}

// 1. SUMMARY METRIC CARDS & HEADER
function loadSummaryCards() {
    const symbol = document.getElementById('symbolSelect').value;
    fetch(`/api/summary-cards?symbol=${symbol}`)
        .then(res => res.json())
        .then(data => {
            if (data.error) return;

            // FII Ratio Card
            const fiiRatio = data.fii_ls_ratio || 50;
            document.getElementById('cardFiiRatio').innerText = `${fiiRatio.toFixed(1)}%`;
            document.getElementById('cardFiiRatioBar').style.width = `${fiiRatio}%`;
            
            const ratioBadge = document.getElementById('cardFiiRatioBadge');
            if (fiiRatio >= 60) {
                ratioBadge.innerText = 'Long Heavy';
                ratioBadge.className = 'text-xs font-semibold px-2 py-0.5 rounded badge-bull';
            } else if (fiiRatio <= 40) {
                ratioBadge.innerText = 'Short Heavy';
                ratioBadge.className = 'text-xs font-semibold px-2 py-0.5 rounded badge-bear';
            } else {
                ratioBadge.innerText = 'Balanced';
                ratioBadge.className = 'text-xs font-semibold px-2 py-0.5 rounded badge-neutral';
            }

            // FII Net Futures Card
            const netFut = data.fii_fut_net || 0;
            const netFutChg = data.fii_fut_net_chg || 0;
            const netFutEl = document.getElementById('cardFiiNetFut');
            netFutEl.innerText = (netFut > 0 ? '+' : '') + netFut.toLocaleString();
            netFutEl.className = `text-2xl font-extrabold ${netFut >= 0 ? 'text-emerald-400' : 'text-red-400'}`;

            const chgEl = document.getElementById('cardFiiNetFutChg');
            chgEl.innerText = `DoD: ${netFutChg >= 0 ? '+' : ''}${netFutChg.toLocaleString()}`;
            chgEl.className = `text-xs font-semibold ${netFutChg >= 0 ? 'text-emerald-400' : 'text-red-400'}`;

            // POC & VWAP Card
            document.getElementById('cardPocPrice').innerText = data.poc ? data.poc.toFixed(2) : '--';
            document.getElementById('cardVwapPrice').innerText = `VWAP: ${data.vwap ? data.vwap.toFixed(2) : '--'}`;
            document.getElementById('cardVpSignal').innerText = data.vp_signal || 'Analyzing...';

            // Max Pain & PCR Card
            document.getElementById('cardMaxPain').innerText = data.max_pain || '--';
            const pcrEl = document.getElementById('cardPcr');
            pcrEl.innerText = `PCR: ${data.pcr || 1.0}`;
            document.getElementById('cardPcrBias').innerText = data.pcr_bias || 'Neutral';
        })
        .catch(err => console.error("Error loading summary cards:", err));
}

// 2. PARTICIPANT-WISE OI & SENTIMENT (MODULE 1)
function loadParticipantData() {
    const selectedDate = document.getElementById('nseDatePicker').value;
    const url = selectedDate ? `/api/fii-dii-oi?date=${selectedDate}` : '/api/fii-dii-oi';

    fetch(url)
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                console.error(data.error);
                return;
            }

            if (data.date_fetched) {
                document.getElementById('fetchedDateTag').innerText = `Date: ${data.date_fetched}`;
            }

            currentParticipantMetrics = data.metrics;
            renderParticipantTable();
            renderSentimentMeter(data.sentiment);
        })
        .catch(err => console.error("Error loading participant data:", err));
}

function renderSentimentMeter(sentiment) {
    if (!sentiment) return;

    const score = sentiment.score || 50;
    const verdict = sentiment.verdict || 'NEUTRAL';
    const retailTrap = sentiment.retail_trap || false;

    // Update Score & Verdict Badge
    document.getElementById('sentimentScore').innerText = score;
    const verdictEl = document.getElementById('sentimentVerdict');
    verdictEl.innerText = verdict;

    if (verdict.includes('BULLISH')) {
        verdictEl.className = 'text-xs font-extrabold uppercase px-3 py-1 rounded-md mt-1 inline-block badge-bull';
    } else if (verdict.includes('BEARISH')) {
        verdictEl.className = 'text-xs font-extrabold uppercase px-3 py-1 rounded-md mt-1 inline-block badge-bear';
    } else {
        verdictEl.className = 'text-xs font-extrabold uppercase px-3 py-1 rounded-md mt-1 inline-block badge-neutral';
    }

    // Needle Rotation (-90 deg at score 0, 0 deg at score 50, +90 deg at score 100)
    const angle = (score / 100) * 180 - 90;
    const needle = document.getElementById('gaugeNeedle');
    if (needle) {
        needle.style.transform = `rotate(${angle}deg)`;
    }

    // Arc Stroke Dashoffset
    const arc = document.getElementById('gaugeArc');
    if (arc) {
        const strokeDash = 125.6;
        const offset = strokeDash - (score / 100) * strokeDash;
        arc.style.strokeDashoffset = offset;
        arc.style.stroke = score >= 60 ? '#10b981' : (score <= 40 ? '#ef4444' : '#f59e0b');
    }

    // Retail Trap Alert Banner
    const trapBanner = document.getElementById('retailTrapBanner');
    if (retailTrap) {
        trapBanner.classList.remove('hidden');
        document.getElementById('retailTrapMsg').innerText = sentiment.trap_reason || 'Retail client positions diverge heavily from Smart Money positions.';
    } else {
        trapBanner.classList.add('hidden');
    }

    // Checklist update
    if (currentParticipantMetrics && currentParticipantMetrics.FII) {
        const fii = currentParticipantMetrics.FII;
        document.getElementById('chkFiiFut').innerText = fii.future_index_net >= 0 ? `Net Long (+${fii.future_index_net.toLocaleString()})` : `Net Short (${fii.future_index_net.toLocaleString()})`;
        document.getElementById('chkFiiFut').className = fii.future_index_net >= 0 ? 'font-semibold text-emerald-400' : 'font-semibold text-red-400';

        document.getElementById('chkFiiCalls').innerText = fii.option_call_net >= 0 ? `Net Long (+${fii.option_call_net.toLocaleString()})` : `Net Short (${fii.option_call_net.toLocaleString()})`;
        document.getElementById('chkFiiCalls').className = fii.option_call_net >= 0 ? 'font-semibold text-emerald-400' : 'font-semibold text-red-400';

        document.getElementById('chkFiiPuts').innerText = fii.option_put_net >= 0 ? `Net Long (+${fii.option_put_net.toLocaleString()})` : `Net Short (${fii.option_put_net.toLocaleString()})`;
        document.getElementById('chkFiiPuts').className = fii.option_put_net >= 0 ? 'font-semibold text-red-400' : 'font-semibold text-emerald-400'; // Long puts = bearish
    }
}

function renderParticipantTable() {
    const tbody = document.getElementById('participantTableBody');
    if (!currentParticipantMetrics) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center py-6 text-gray-500">No Data Available</td></tr>';
        return;
    }

    let rowsHtml = '';
    const order = ['FII', 'DII', 'Pro', 'Client'];

    order.forEach(participant => {
        const item = currentParticipantMetrics[participant];
        if (!item) return;

        let longVal = 0, shortVal = 0, netVal = 0, chgVal = 0;

        if (activeTab === 'idxFut') {
            longVal = item.future_index_long;
            shortVal = item.future_index_short;
            netVal = item.future_index_net;
            chgVal = item.future_index_net_chg;
        } else if (activeTab === 'idxCall') {
            longVal = item.option_call_long;
            shortVal = item.option_call_short;
            netVal = item.option_call_net;
            chgVal = item.option_call_net_chg;
        } else if (activeTab === 'idxPut') {
            longVal = item.option_put_long;
            shortVal = item.option_put_short;
            netVal = item.option_put_net;
            chgVal = item.option_put_net_chg;
        } else if (activeTab === 'stkFut') {
            longVal = item.future_stock_long;
            shortVal = item.future_stock_short;
            netVal = item.future_stock_net;
            chgVal = item.future_stock_net_chg;
        }

        const lsRatio = (longVal + shortVal) > 0 ? (longVal / (longVal + shortVal) * 100).toFixed(1) : 50;
        const netColor = netVal >= 0 ? 'text-emerald-400 font-bold' : 'text-red-400 font-bold';
        const chgColor = chgVal >= 0 ? 'text-emerald-400' : 'text-red-400';

        rowsHtml += `
            <tr>
                <td class="font-bold text-white flex items-center space-x-2">
                    <span class="w-2 h-2 rounded-full ${participant === 'FII' ? 'bg-blue-400' : participant === 'DII' ? 'bg-emerald-400' : participant === 'Pro' ? 'bg-purple-400' : 'bg-amber-400'}"></span>
                    <span>${participant === 'Client' ? 'Client (Retail)' : participant === 'Pro' ? 'Pro (Prop Desks)' : participant}</span>
                </td>
                <td class="text-right font-mono">${longVal.toLocaleString()}</td>
                <td class="text-right font-mono">${shortVal.toLocaleString()}</td>
                <td class="text-right font-mono ${netColor}">${netVal >= 0 ? '+' : ''}${netVal.toLocaleString()}</td>
                <td class="text-right font-mono ${chgColor}">${chgVal >= 0 ? '+' : ''}${chgVal.toLocaleString()}</td>
                <td class="text-center">
                    <div class="flex items-center justify-center space-x-2">
                        <span class="text-xs font-mono w-10">${lsRatio}%</span>
                        <div class="w-16 bg-[#1a2336] rounded-full h-1.5 overflow-hidden">
                            <div class="h-1.5 rounded-full ${lsRatio >= 50 ? 'bg-emerald-500' : 'bg-red-500'}" style="width: ${lsRatio}%"></div>
                        </div>
                    </div>
                </td>
            </tr>
        `;
    });

    tbody.innerHTML = rowsHtml;
}

// 3. VOLUME PROFILE ENGINE (MODULE 2)
function loadVolumeProfile() {
    const symbol = document.getElementById('symbolSelect').value;
    fetch(`/api/volume-profile?symbol=${symbol}`)
        .then(res => res.json())
        .then(data => {
            if (!data) return;

            document.getElementById('vpCurrentPrice').innerText = data.current_price.toFixed(2);
            document.getElementById('vpPoc').innerText = data.poc.toFixed(2);
            document.getElementById('vpValVah').innerText = `${data.val.toFixed(2)} - ${data.vah.toFixed(2)}`;
            
            const badge = document.getElementById('vpSignalBadge');
            badge.innerText = data.signal_code || 'BALANCED';
            if (data.signal_code === 'MARKUP') {
                badge.className = 'text-xs font-extrabold px-2 py-0.5 rounded badge-bull';
            } else if (data.signal_code === 'MARKDOWN') {
                badge.className = 'text-xs font-extrabold px-2 py-0.5 rounded badge-bear';
            } else if (data.signal_code === 'POC_RETEST') {
                badge.className = 'text-xs font-extrabold px-2 py-0.5 rounded badge-neutral';
            } else {
                badge.className = 'text-xs font-extrabold px-2 py-0.5 rounded bg-gray-800 text-gray-300 border border-gray-700';
            }

            document.getElementById('vpExplanation').innerText = data.explanation || '';

            renderVolumeProfileChart(data);
        })
        .catch(err => console.error("Error loading volume profile:", err));
}

function renderVolumeProfileChart(vpData) {
    const ctx = document.getElementById('volumeProfileChart').getContext('2d');

    if (vpChartInstance) {
        vpChartInstance.destroy();
    }

    const profile = vpData.profile || [];
    const labels = profile.map(p => p.price_mid.toFixed(2));
    const volumes = profile.map(p => p.volume);

    // Color bars: Gold/Yellow for POC, Cyan for Value Area, Dark slate for outside VA
    const backgroundColors = profile.map(p => {
        if (p.is_poc) return '#f59e0b'; // Amber POC
        if (p.in_value_area) return 'rgba(56, 189, 248, 0.6)'; // Value Area Sky Blue
        return 'rgba(51, 65, 85, 0.4)'; // Outside VA
    });

    const borderColors = profile.map(p => {
        if (p.is_poc) return '#fbbf24';
        if (p.in_value_area) return '#38bdf8';
        return '#475569';
    });

    vpChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Volume Traded',
                data: volumes,
                backgroundColor: backgroundColors,
                borderColor: borderColors,
                borderWidth: 1,
                borderRadius: 2
            }]
        },
        options: {
            indexAxis: 'y', // Horizontal Volume Profile
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => ` Traded Vol: ${ctx.parsed.x.toLocaleString()}`
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8' },
                    title: { display: true, text: 'Traded Volume', color: '#64748b', font: { size: 10 } }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#cbd5e1', font: { size: 9 } },
                    title: { display: true, text: 'Price Levels', color: '#64748b', font: { size: 10 } }
                }
            }
        }
    });
}

// 4. BIG MONEY OPTION CONCENTRATION (MODULE 3)
function loadOptionChain() {
    const symbol = document.getElementById('symbolSelect').value;
    fetch(`/api/option-chain?symbol=${symbol}`)
        .then(res => res.json())
        .then(data => {
            if (!data) return;

            document.getElementById('callWallStrike').innerText = data.call_wall ? data.call_wall.strike : '--';
            document.getElementById('callWallOi').innerText = data.call_wall ? `OI: ${data.call_wall.oi.toLocaleString()}` : 'OI: --';

            document.getElementById('putWallStrike').innerText = data.put_wall ? data.put_wall.strike : '--';
            document.getElementById('putWallOi').innerText = data.put_wall ? `OI: ${data.put_wall.oi.toLocaleString()}` : 'OI: --';

            // Unwinding alerts
            const alertList = document.getElementById('unwindingAlertsList');
            if (data.unwinding_alerts && data.unwinding_alerts.length > 0) {
                let html = '';
                data.unwinding_alerts.forEach(a => {
                    html += `
                        <div class="p-2 rounded bg-[#1e293b]/60 border-l-2 ${a.type === 'CALL_SHORT_COVERING' ? 'border-emerald-500 text-emerald-300' : 'border-red-500 text-red-300'}">
                            <span class="font-bold">${a.type.replace(/_/g, ' ')}</span>: ${a.msg}
                        </div>
                    `;
                });
                alertList.innerHTML = html;
            } else {
                alertList.innerHTML = '<p class="text-gray-500 italic">No major unwinding detected.</p>';
            }

            renderOptionOiChart(data);
        })
        .catch(err => console.error("Error loading option chain:", err));
}

function renderOptionOiChart(optData) {
    const ctx = document.getElementById('optionOiChart').getContext('2d');

    if (optChartInstance) {
        optChartInstance.destroy();
    }

    const chain = optData.chain || [];
    const strikes = chain.map(c => c.strike);
    const callOis = chain.map(c => c.call_oi);
    const putOis = chain.map(c => c.put_oi);

    optChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: strikes,
            datasets: [
                {
                    label: 'Call OI (Resistance)',
                    data: callOis,
                    backgroundColor: 'rgba(239, 68, 68, 0.7)',
                    borderColor: '#ef4444',
                    borderWidth: 1
                },
                {
                    label: 'Put OI (Support)',
                    data: putOis,
                    backgroundColor: 'rgba(16, 185, 129, 0.7)',
                    borderColor: '#10b981',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#cbd5e1' }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8', font: { size: 10 } }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8' }
                }
            }
        }
    });
}
