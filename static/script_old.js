// Socket.IO connection
const socket = io();

// Global state
let currentRole = {
    name: '',
    type: '',
    description: '',
    sees: []
};
let roomCode = '';
let playerName = '';
let isGameMaster = false;
let selectedTeam = [];

// Available roles
const AVAILABLE_ROLES = {
    'merlin': 'Merlin',
    'perceval': 'Perceval',
    'morgane': 'Morgane',
    'oberon': 'Oberon (Hidden Spy)',
    'mordred': 'Mordred (Hidden Spy)',
    'minions': 'Minion of Morgane',
    'lancelot': 'Lancelot (Traitor)',
    'guinevere': 'Guinevere',
    'tristan': 'Tristan',
    'iseult': 'Iseult',
    'vivien': 'Vivien',
    'loyal_servant': 'Loyal Servant'
};

// UI Navigation
function showGameMasterScreen() {
    document.getElementById('home-screen').classList.remove('active');
    document.getElementById('gm-screen').classList.add('active');
    document.getElementById('player-join-screen').classList.remove('active');
    document.getElementById('player-game-screen').classList.remove('active');
    isGameMaster = true;
    populateRoleCheckboxes();
}

function showPlayerJoinScreen() {
    document.getElementById('home-screen').classList.remove('active');
    document.getElementById('player-join-screen').classList.add('active');
    document.getElementById('gm-screen').classList.remove('active');
}

function goHome() {
    document.getElementById('home-screen').classList.add('active');
    document.getElementById('player-join-screen').classList.remove('active');
    document.getElementById('gm-screen').classList.remove('active');
    document.getElementById('player-game-screen').classList.remove('active');
}

// Game Master Functions
function createGame() {
    socket.emit('create_game', {});
}

function populateRoleCheckboxes() {
    const container = document.getElementById('role-checkboxes');
    container.innerHTML = '';
    
    for (const [key, name] of Object.entries(AVAILABLE_ROLES)) {
        const label = document.createElement('label');
        label.className = 'role-checkbox';
        label.innerHTML = `
            <input type="checkbox" id="role-${key}" value="${key}">
            <span>${name}</span>
        `;
        container.appendChild(label);
    }
}

function assignRoles() {
    const checkboxes = document.querySelectorAll('#role-checkboxes input:checked');
    const selectedRoles = Array.from(checkboxes).map(cb => cb.value);
    
    if (selectedRoles.length === 0) {
        alert('Select at least one role');
        return;
    }
    
    socket.emit('assign_roles', {
        room_code: roomCode,
        roles: selectedRoles
    });
}

function revealRoles() {
    socket.emit('reveal_roles', {
        room_code: roomCode
    });
}

function startNextQuest() {
    // Start next quest workflow
    showQuestTeamProposal();
}

function proposeTeam() {
    // GM manually selects team members
    const playersList = document.getElementById('gm-players-list').querySelectorAll('li');
    const playerNames = Array.from(playersList).map(li => li.textContent);
    
    alert('Select team members from the list above (manually for now)');
}

function startQuestMission() {
    socket.emit('quest_mission_start', {
        room_code: roomCode
    });
}

function endQuestMission() {
    socket.emit('end_quest_mission', {
        room_code: roomCode,
        quest_num: document.getElementById('current-quest-info').dataset.questNum || 1
    });
}

function nextQuest() {
    // Move to next quest
    const currentNum = parseInt(document.getElementById('current-quest-info').dataset.questNum) || 1;
    updateQuestInfo(currentNum + 1);
}

function endGame() {
    if (confirm('End the game? This cannot be undone.')) {
        goHome();
    }
}

// Player Functions
function joinGame() {
    const code = document.getElementById('join-room-code').value.toUpperCase();
    const name = document.getElementById('player-name').value;
    
    if (!code || !name) {
        alert('Enter room code and name');
        return;
    }
    
    roomCode = code;
    playerName = name;
    
    socket.emit('join_game', {
        room_code: code,
        player_name: name
    });
}

function voteTeam(approve) {
    socket.emit('vote_team', {
        room_code: roomCode,
        vote: approve
    });
}

function questMissionVote(success) {
    socket.emit('quest_mission_votes', {
        room_code: roomCode,
        quest_num: document.getElementById('player-quest-mission').dataset.questNum || 1,
        vote: success
    });
}

// Socket.IO Event Handlers

// Game Master events
socket.on('game_created', (data) => {
    roomCode = data.room_code;
    document.getElementById('room-code-display').textContent = roomCode;
    document.getElementById('gm-create').classList.add('hidden');
    document.getElementById('gm-lobby').classList.remove('hidden');
    
    console.log('Game created with code:', roomCode);
});

socket.on('player_joined', (data) => {
    if (isGameMaster) {
        updateGMPlayersList(data.players);
    }
});

socket.on('roles_assigned', (data) => {
    document.getElementById('gm-lobby').classList.add('hidden');
    document.getElementById('gm-game').classList.remove('hidden');
    console.log(data.message);
});

socket.on('quest_vote_result', (data) => {
    console.log('Team vote result:', data);
    // Update UI with vote results
});

socket.on('quest_result', (data) => {
    console.log('Quest result:', data);
    updateQuestResults(data);
});

// Player events
socket.on('error', (data) => {
    alert('Error: ' + data.message);
});

socket.on('reveal_roles_10s', (data) => {
    const playerView = data.player_views[socket.id];
    
    // Show role name first
    const roleDisplay = document.getElementById('role-display');
    roleDisplay.innerHTML = `
        <div class="role-name">${playerView.role.role_name}</div>
        <div class="role-type">${playerView.role.type}</div>
        <div class="role-description">${playerView.role.description}</div>
    `;
    
    // Show special info for 10 seconds
    if (Object.keys(playerView.special_info).length > 0) {
        const infoHtml = formatSpecialInfo(playerView.special_info);
        roleDisplay.innerHTML += `<div class="special-info">${infoHtml}</div>`;
        
        setTimeout(() => {
            roleDisplay.innerHTML = `
                <div class="role-name">${playerView.role.role_name}</div>
                <div class="role-type">${playerView.role.type}</div>
            `;
        }, 10000);
    }
    
    document.getElementById('player-role-reveal').classList.remove('hidden');
    setTimeout(() => {
        document.getElementById('player-role-reveal').classList.add('hidden');
    }, data.duration * 1000 + 1000);
});

socket.on('team_proposed', (data) => {
    document.getElementById('team-info').textContent = 
        `Team proposed by ${data.proposed_by}: ${data.team.join(', ')}`;
    document.getElementById('player-team-vote').classList.remove('hidden');
});

socket.on('player_joined', (data) => {
    if (!isGameMaster) {
        updatePlayerPlayersList(data.players);
        roomCode = data.room_code;
        document.getElementById('player-room-code').textContent = roomCode;
        
        // Switch to player game screen
        document.getElementById('player-join-screen').classList.add('hidden');
        document.getElementById('player-game-screen').classList.add('active');
    }
});

// Helper Functions

function updateGMPlayersList(players) {
    const list = document.getElementById('gm-players-list');
    list.innerHTML = '';
    
    for (const [playerId, player] of Object.entries(players)) {
        const li = document.createElement('li');
        li.textContent = player.name + (player.connected ? '' : ' (Disconnected)');
        list.appendChild(li);
    }
}

function updatePlayerPlayersList(players) {
    const list = document.getElementById('player-players-list');
    list.innerHTML = '';
    
    for (const [playerId, player] of Object.entries(players)) {
        const li = document.createElement('li');
        li.textContent = player.name;
        list.appendChild(li);
    }
}

function formatSpecialInfo(info) {
    let html = '<strong>You can see:</strong><br>';
    
    if (info.sees_spies) {
        html += `Spies: ${info.sees_spies.join(', ')}<br>`;
    }
    if (info.sees_names) {
        html += `Names: ${info.sees_names.join(', ')}<br>`;
    }
    if (info.sees_merlin) {
        html += `Merlin: ${info.sees_merlin}<br>`;
    }
    if (info.sees_iseult) {
        html += `Iseult: ${info.sees_iseult}<br>`;
    }
    if (info.sees_tristan) {
        html += `Tristan: ${info.sees_tristan}<br>`;
    }
    
    return html;
}

function updateQuestResults(data) {
    const resultsDiv = document.getElementById('quest-results');
    const result = document.createElement('div');
    result.className = `quest-result ${data.succeeds ? 'success' : 'fail'}`;
    result.textContent = data.succeeds ? '✓' : '✗';
    resultsDiv.appendChild(result);
    
    updateQuestScore();
}

function updateQuestScore() {
    const results = document.querySelectorAll('.quest-result');
    const successes = Array.from(results).filter(r => r.classList.contains('success')).length;
    const failures = results.length - successes;
    document.getElementById('quest-score').textContent = `${successes}-${failures}`;
}

function updateQuestInfo(questNum) {
    const questSizes = [0, 3, 4, 4, 5, 5];
    const size = questSizes[questNum] || 5;
    
    document.getElementById('current-quest-info').textContent = `Quest ${questNum} - Team size: ${size}`;
    document.getElementById('current-quest-info').dataset.questNum = questNum;
}

function showQuestTeamProposal() {
    // Show UI for proposing a team
    const playersList = document.getElementById('gm-players-list').querySelectorAll('li');
    console.log('GM: Propose a team from these players');
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('Avalon app loaded');
});
