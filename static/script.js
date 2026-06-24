const socket = io();

let roomCode = '';
let playerName = '';
let isGameMaster = false;
let gameState = 'waiting';
let selectedRoles = [];
let availableRoles = {};
let roleAssignments = {};

// Navigation
function showGMScreen() {
    switchScreen('home-screen', 'gm-screen');
    isGameMaster = true;
}

function showPlayerJoinScreen() {
    switchScreen('home-screen', 'player-join-screen');
}

function goHome() {
    switchScreen('player-join-screen', 'home-screen');
}

function switchScreen(fromId, toId) {
    document.getElementById(fromId).classList.remove('active');
    document.getElementById(toId).classList.add('active');
}

// Game Master Functions
function createGame() {
    socket.emit('create_game', {});
}

function startRoleAssignment() {
    if (selectedRoles.length === 0) {
        alert('Sélectionne au moins un rôle');
        return;
    }
    
    socket.emit('start_assignment', {
        room_code: roomCode
    });
}

function confirmAssignments() {
    socket.emit('confirm_assignments', {
        room_code: roomCode
    });
}

function backToRoleSelection() {
    document.getElementById('gm-assignment').classList.add('hidden');
    document.getElementById('gm-lobby').classList.remove('hidden');
}

function assignRoleToPlayer(playerId, roleKey) {
    roleAssignments[playerId] = roleKey;
    
    // Update UI
    const cell = document.querySelector(`[data-player="${playerId}"]`);
    if (cell) {
        cell.textContent = roleKey;
        cell.style.backgroundColor = '#27ae60';
    }
    
    socket.emit('assign_player_role', {
        room_code: roomCode,
        player_id: playerId,
        role_key: roleKey
    });
}

function revealRoles() {
    socket.emit('reveal_roles', {
        room_code: roomCode
    });
}

// Placeholder functions pour boutons du jeu
function startQuest1() { console.log('Start Quest 1'); }
function proposeTeam() { console.log('Propose Team'); }
function teamVoteResults() { console.log('Team Vote Results'); }
function startMission() { console.log('Start Mission'); }
function missionResults() { console.log('Mission Results'); }
function nextQuest() { console.log('Next Quest'); }
function endGame() {
    if (confirm('Terminer la partie?')) {
        goHome();
    }
}

// Player Functions
function joinGame() {
    const code = document.getElementById('join-room-code').value.toUpperCase();
    const name = document.getElementById('player-name').value;
    
    if (!code || !name) {
        alert('Remplis le code et ton nom');
        return;
    }
    
    roomCode = code;
    playerName = name;
    
    socket.emit('join_game', {
        room_code: code,
        player_name: name
    });
}

// Socket.IO Events

socket.on('game_created', (data) => {
    roomCode = data.room_code;
    document.getElementById('room-code-display').textContent = roomCode;
    document.getElementById('gm-create').classList.add('hidden');
    document.getElementById('gm-lobby').classList.remove('hidden');
    
    // Charge les rôles disponibles
    socket.emit('get_compatible_roles', {
        room_code: roomCode
    });
});

socket.on('compatible_roles', (data) => {
    availableRoles = data.roles;
    displayRoleSelection();
});

socket.on('roles_updated', (data) => {
    selectedRoles = data.selected_roles;
    socket.emit('get_compatible_roles', {
        room_code: roomCode
    });
});

socket.on('player_joined', (data) => {
    if (isGameMaster) {
        updateGMPlayersList(data.players);
    } else {
        updatePlayerList(data.players);
        document.getElementById('player-room-code').textContent = data.room_code;
    }
});

socket.on('ready_to_assign', (data) => {
    document.getElementById('gm-lobby').classList.add('hidden');
    document.getElementById('gm-assignment').classList.remove('hidden');
    displayRoleAssignmentInterface(data.players, data.available_roles);
});

socket.on('assignments_confirmed', (data) => {
    document.getElementById('gm-assignment').classList.add('hidden');
    document.getElementById('gm-game').classList.remove('hidden');
});

socket.on('reveal_roles_10s', (data) => {
    const playerView = data.player_views[socket.id];
    
    if (playerView) {
        displayRoleReveal(playerView, data.duration);
    }
});

socket.on('error', (data) => {
    alert('Erreur: ' + data.message);
});

// UI Update Functions

function displayRoleSelection() {
    const container = document.getElementById('role-selection-grid');
    container.innerHTML = '';
    
    // Group by type
    const loyalists = availableRoles.filter(r => r.type === 'loyalist');
    const spies = availableRoles.filter(r => r.type === 'spy');
    
    // Loyalists
    const loyalistSection = document.createElement('div');
    loyalistSection.className = 'role-section';
    loyalistSection.innerHTML = '<h5>Loyalistes</h5>';
    
    loyalists.forEach(role => {
        const label = document.createElement('label');
        label.className = 'role-checkbox';
        if (!role.enabled) {
            label.style.opacity = '0.5';
            label.title = role.reason;
        }
        
        label.innerHTML = `
            <input type="checkbox" value="${role.key}" ${role.selected ? 'checked' : ''} 
                   ${role.enabled ? '' : 'disabled'} 
                   onchange="toggleRole('${role.key}')">
            <span>${role.name}</span>
            <small>${role.description}</small>
        `;
        loyalistSection.appendChild(label);
    });
    container.appendChild(loyalistSection);
    
    // Spies
    const spySection = document.createElement('div');
    spySection.className = 'role-section';
    spySection.innerHTML = '<h5>Espions</h5>';
    
    spies.forEach(role => {
        const label = document.createElement('label');
        label.className = 'role-checkbox';
        if (!role.enabled) {
            label.style.opacity = '0.5';
            label.title = role.reason;
        }
        
        label.innerHTML = `
            <input type="checkbox" value="${role.key}" ${role.selected ? 'checked' : ''} 
                   ${role.enabled ? '' : 'disabled'} 
                   onchange="toggleRole('${role.key}')">
            <span>${role.name}</span>
            <small>${role.description}</small>
        `;
        spySection.appendChild(label);
    });
    container.appendChild(spySection);
}

function toggleRole(roleKey) {
    socket.emit('toggle_role', {
        room_code: roomCode,
        role_key: roleKey
    });
}

function updateGMPlayersList(players) {
    const list = document.getElementById('gm-players-list');
    list.innerHTML = '';
    
    for (const [playerId, player] of Object.entries(players)) {
        const li = document.createElement('li');
        li.textContent = player.name;
        list.appendChild(li);
    }
}

function updatePlayerList(players) {
    const list = document.getElementById('player-players-list');
    list.innerHTML = '';
    
    for (const [playerId, player] of Object.entries(players)) {
        const li = document.createElement('li');
        li.textContent = player.name;
        list.appendChild(li);
    }
}

function displayRoleAssignmentInterface(players, selectedRoles) {
    const container = document.getElementById('assignment-grid');
    container.innerHTML = '';
    
    players.forEach(player => {
        const div = document.createElement('div');
        div.className = 'assignment-row';
        
        const nameSpan = document.createElement('span');
        nameSpan.className = 'player-name';
        nameSpan.textContent = player.name;
        
        const select = document.createElement('select');
        select.className = 'role-select';
        select.onchange = (e) => assignRoleToPlayer(player.id, e.target.value);
        
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = '-- Sélectionne un rôle --';
        select.appendChild(defaultOption);
        
        selectedRoles.forEach(roleKey => {
            const option = document.createElement('option');
            option.value = roleKey;
            option.textContent = roleKey;
            select.appendChild(option);
        });
        
        div.appendChild(nameSpan);
        div.appendChild(select);
        container.appendChild(div);
    });
}

function displayRoleReveal(playerView, duration) {
    const display = document.getElementById('player-role-display');
    
    // Show role name and description
    let html = `
        <div class="role-name">${playerView.role.role_name}</div>
        <div class="role-type">${playerView.role.type}</div>
        <div class="role-description">${playerView.role.description}</div>
    `;
    
    // Show special info if available
    if (playerView.special_info && Object.keys(playerView.special_info).length > 0) {
        const info = playerView.special_info;
        html += '<div class="special-info">';
        
        if (info.type === 'spies') {
            html += '<strong>Tu vois les espions:</strong><br>' + info.names.join(', ');
        } else if (info.type === 'two_names') {
            html += '<strong>Tu vois deux noms (pas qui est qui):</strong><br>' + info.names.join(', ');
        } else if (info.type === 'one_name') {
            html += '<strong>Tu vois:</strong><br>' + info.name;
        }
        
        html += '</div>';
    }
    
    display.innerHTML = html;
    
    // Show the reveal section
    document.getElementById('player-waiting').classList.add('hidden');
    document.getElementById('player-role-reveal').classList.remove('hidden');
    
    // Hide after duration + 2 seconds
    setTimeout(() => {
        document.getElementById('player-role-reveal').classList.add('hidden');
        document.getElementById('player-game-waiting').classList.remove('hidden');
    }, (duration + 2) * 1000);
}
