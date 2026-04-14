let currentTab = 'officials';
let customsData = [];
let officialsData = [];
let pendingChanges = {"customs":[],"officials":[]};

function showMessage(message, type = 'info') {
    const messageArea = document.getElementById('message-area');
    const className = type === 'error' ? 'error' : 'success';
    messageArea.innerHTML = `<div class="${className}">${message}</div>`;
    setTimeout(() => {
        messageArea.innerHTML = '';
    }, 5000);
}

async function loadData() {
    if (currentTab === 'officials'){
        // get all IDs
        const ids = await (await fetch("/ids/officials")).json();
        console.log(ids);
        // are there any new IDs? if so, download full data of new IDs, clear old and populate new
            document.querySelector('#officials-table tbody').innerHTML = '';
            document.getElementById('loading').style.display = 'block';
            // write the new stuff, do not put it in the DOC until ready
            document.getElementById('officials-stats').innerHTML = '';
            // update the stats similarly
            showMessage('Data loaded successfully!', 'success');
            document.getElementById('loading').style.display = 'none';
    }
    else if(currentTab === 'customs'){
        document.getElementById('customs-stats').innerHTML = '';
        document.querySelector('#customs-table tbody').innerHTML = '';
    }
}

function switchTab(tab) {
    currentTab = tab;
    
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelector(`.tab:nth-child(${tab === 'customs' ? 2 : 1})`).classList.add('active');
    
    // Show/hide content
    document.getElementById('customs-content').style.display = tab === 'customs' ? 'block' : 'none';
    document.getElementById('officials-content').style.display = tab === 'officials' ? 'block' : 'none';

    loadData();
}

// function updatePendingChangesDisplay() {
//     const totalPending = pendingChanges.customs.length + pendingChanges.officials.length;
//     const wantedCell = document.getElementById('wanted-header');

//     if (totalPending > 0) {
//         wantedCell.style.backgroundColor = 'yellow';
//     } else {
//         wantedCell.style.backgroundColor = '';
//     }
// }

// function updateStats() {
//     // Update customs stats
//     const customsWanted = customsData.filter(song => song.wanted).length;
//     const customsTotal = customsData.length;
//     const customsFullBand = customsData.filter(song => 
//         song.diff_drums !== null && song.diff_drums !== -1 &&
//         song.diff_guitar !== null && song.diff_guitar !== -1 &&
//         song.diff_bass !== null && song.diff_bass !== -1 &&
//         song.diff_vocals !== null && song.diff_vocals !== -1
//     ).length;

//     document.getElementById('customs-stats').innerHTML = `
//         <div class="stat-card">
//             <div class="stat-number">${customsTotal}</div>
//             <div class="stat-label">Total Customs</div>
//         </div>
//         <div class="stat-card">
//             <div class="stat-number">${customsWanted}</div>
//             <div class="stat-label">Wanted Customs</div>
//         </div>
//         <div class="stat-card">
//             <div class="stat-number">${customsFullBand}</div>
//             <div class="stat-label">Full Band Songs</div>
//         </div>
//     `;

//     // Update officials stats
//     const officialsWanted = officialsData.filter(song => song.wanted).length;
//     const officialsTotal = officialsData.length;

//     document.getElementById('officials-stats').innerHTML = `
//         <div class="stat-card">
//             <div class="stat-number">${officialsTotal}</div>
//             <div class="stat-label">Total Officials</div>
//         </div>
//         <div class="stat-card">
//             <div class="stat-number">${officialsWanted}</div>
//             <div class="stat-label">Wanted Officials</div>
//         </div>
//     `;
// }

// function renderCustomsTable() {
//     const tbody = document.querySelector('#customs-table tbody');
//     tbody.innerHTML = '';

//     customsData.forEach((song, index) => {
//         const isFullBand = song.diff_drums !== null && song.diff_drums !== -1 &&
//                             song.diff_guitar !== null && song.diff_guitar !== -1 &&
//                             song.diff_bass !== null && song.diff_bass !== -1 &&
//                             song.diff_vocals !== null && song.diff_vocals !== -1;

//         const row = document.createElement('tr');
//         row.innerHTML = `
//             <td class="wanted-cell">
//                 <input type="checkbox" class="wanted-checkbox" 
//                         ${song.wanted ? 'checked' : ''} 
//                         onchange="updateWanted('customs', ${index}, this.checked)">
//             </td>
//             <td class="song-title" title="${song.title || ''}">${song.title || 'Unknown'}</td>
//             <td class="song-artist" title="${song.artist || ''}">${song.artist || 'Unknown'}</td>
//             <td class="full-band">
//                 ${isFullBand ? ' ✅ ' : ' ❌ '}
//             </td>
//         `;
//         tbody.appendChild(row);
//     });
// }

// function renderOfficialsTable() {
//     const tbody = document.querySelector('#officials-table tbody');
//     tbody.innerHTML = '';

//     officialsData.forEach((song, index) => {
//         const row = document.createElement('tr');
//         row.innerHTML = `
//             <td class="wanted-cell">
//                 <input type="checkbox" class="wanted-checkbox" 
//                         ${song.wanted ? 'checked' : ''} 
//                         onchange="updateWanted('officials', ${index}, this.checked)">
//             </td>
//             <td class="song-title" title="${song.title || ''}">${song.title || 'Unknown'}</td>
//             <td class="song-artist" title="${song.artist || ''}">${song.artist || 'Unknown'}</td>
//         `;
//         tbody.appendChild(row);
//     });
// }

// function updateWanted(table, index, wanted) {
//     if (table === 'customs') {
//         customsData[index].wanted = wanted;

//         const fileId = customsData[index].file_id;

//         const existsIndex = pendingChanges.customs.findIndex(change =>
//             change.file_id === fileId
//         );

//         if (existsIndex !== -1) {
//             // Remove existing entry
//             pendingChanges.customs.splice(existsIndex, 1);
//         } else {
//             // Add new entry
//             pendingChanges.customs.push({
//                 file_id: fileId,
//                 wanted: customsData[index].wanted
//             });
//         }

//     } else {
//         officialsData[index].wanted = wanted;

//         const title = officialsData[index].title;
//         const artist = officialsData[index].artist;

//         const existsIndex = pendingChanges.officials.findIndex(change =>
//             change.title === title && change.artist === artist
//         );

//         if (existsIndex !== -1) {
//             // Remove existing entry
//             pendingChanges.officials.splice(existsIndex, 1);
//         } else {
//             // Add new entry
//             pendingChanges.officials.push({
//                 title: title,
//                 artist: artist,
//                 wanted: officialsData[index].wanted
//             });
//         }
//     }

//     updateStats();
//     updatePendingChangesDisplay();
// }

// async function saveChanges() {
//     if (pendingChanges.size === 0) {
//         showMessage('No changes to save.', 'info');
//         return;
//     }

//     const customs = pendingChanges.customs;
//     const officials = pendingChanges.officials;
//     console.log(customs);

//     try {
//         if (customs.length > 0) {
//             await fetch('/api/customs/update', {
//                 method: 'POST',
//                 headers: {
//                     'Content-Type': 'application/json',
//                 },
//                 body: JSON.stringify({ updates: customs }),
//             });
//         }

//         if (officials.length > 0) {
//             await fetch('/api/officials/update', {
//                 method: 'POST',
//                 headers: {
//                     'Content-Type': 'application/json',
//                 },
//                 body: JSON.stringify({ updates: officials }),
//             });
//         }

//         const totalChanges = customs.length + officials.length;
//         pendingChanges = {"customs":[],"officials":[]};
//         updatePendingChangesDisplay();
//         showMessage(`Successfully saved ${totalChanges} changes!`, 'success');
//     } catch (error) {
//         showMessage('Error saving changes: ' + error.message, 'error');
//     }
// }

// Load data when page loads
window.addEventListener('load', loadData);