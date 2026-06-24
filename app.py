from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import secrets
import random
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
socketio = SocketIO(app, cors_allowed_origins="*")

# Store active games in memory (stateless)
games = {}

# Role definitions
ROLES = {
    'LOYALISTS': {
        'merlin': {
            'name': 'Merlin',
            'type': 'loyalist',
            'description': 'Knows all spies except Morgane',
            'sees': 'all_spies_except_morgane'
        },
        'perceval': {
            'name': 'Perceval',
            'type': 'loyalist',
            'description': 'Knows Merlin and Morgane but not which is which',
            'sees': 'merlin_and_morgane'
        },
        'guinevere': {
            'name': 'Guinevere',
            'type': 'loyalist',
            'description': 'Knows Merlin only',
            'sees': 'merlin_only'
        },
        'tristan': {
            'name': 'Tristan',
            'type': 'loyalist',
            'description': 'Knows Iseult',
            'sees': 'iseult_only'
        },
        'iseult': {
            'name': 'Iseult',
            'type': 'loyalist',
            'description': 'Knows Tristan',
            'sees': 'tristan_only'
        },
        'vivien': {
            'name': 'Vivien',
            'type': 'loyalist',
            'description': 'Loyalist who knows Merlin',
            'sees': 'merlin_only'
        },
        'loyal_servant': {
            'name': 'Loyal Servant',
            'type': 'loyalist',
            'description': 'Vanilla loyalist',
            'sees': 'nothing'
        }
    },
    'SPIES': {
        'morgane': {
            'name': 'Morgane',
            'type': 'spy',
            'description': 'Spy. Tricks Merlin. Knows all spies',
            'sees': 'all_spies'
        },
        'oberon': {
            'name': 'Oberon',
            'type': 'spy',
            'description': 'Hidden spy. Knows all spies',
            'sees': 'all_spies'
        },
        'mordred': {
            'name': 'Mordred',
            'type': 'spy',
            'description': 'Hidden spy. Knows no one. No one knows him',
            'sees': 'nothing'
        },
        'minions': {
            'name': 'Minion of Morgane',
            'type': 'spy',
            'description': 'Spy who knows Merlin and tries to unmask him',
            'sees': 'merlin_only'
        },
        'lancelot': {
            'name': 'Lancelot (Traitor)',
            'type': 'spy',
            'description': 'Spy pretending to be loyal',
            'sees': 'all_spies'
        },
        'minion': {
            'name': 'Minion',
            'type': 'spy',
            'description': 'Vanilla spy',
            'sees': 'all_spies'
        }
    }
}

class Game:
    def __init__(self, room_code, game_master_id):
        self.room_code = room_code
        self.game_master_id = game_master_id
        self.players = {}
        self.game_state = 'waiting'
        self.current_quest = 0
        self.quest_results = []
        self.active_roles = []
        self.role_assignments = {}
        self.quest_votes = {}
        self.current_team = []
        self.team_proposal_by = None
        self.timestamp = datetime.now()

    def to_dict(self):
        return {
            'room_code': self.room_code,
            'game_master_id': self.game_master_id,
            'players': self.players,
            'game_state': self.game_state,
            'current_quest': self.current_quest,
            'quest_results': self.quest_results,
            'active_roles': self.active_roles,
            'role_assignments': self.role_assignments,
            'current_team': self.current_team
        }

def generate_room_code():
    return ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))

def assign_roles(num_players, active_roles):
    if 'merlin' in active_roles and 'morgane' not in active_roles:
        active_roles.append('morgane')
    
    if 'perceval' in active_roles and 'merlin' not in active_roles and 'morgane' not in active_roles:
        active_roles.append('merlin')
    
    if 'minions' in active_roles and 'morgane' not in active_roles:
        active_roles.append('morgane')
    
    num_loyalists = max(2, num_players // 2 - 1)
    num_spies = num_players - num_loyalists
    
    assignment = []
    assigned_roles = set()
    
    for role in active_roles:
        if role in ROLES['LOYALISTS']:
            assignment.append(role)
            assigned_roles.add(role)
        elif role in ROLES['SPIES']:
            assignment.append(role)
            assigned_roles.add(role)
    
    num_assigned = len(assignment)
    if num_assigned > num_players:
        while num_assigned > num_players and assignment:
            assignment.pop()
            num_assigned -= 1
    
    loyal_count = sum(1 for r in assignment if r in ROLES['LOYALISTS'])
    spy_count = sum(1 for r in assignment if r in ROLES['SPIES'])
    
    while len(assignment) < num_players:
        if loyal_count < num_loyalists:
            assignment.append('loyal_servant')
            loyal_count += 1
        elif spy_count < num_spies:
            assignment.append('minion')
            spy_count += 1
        else:
            break
    
    random.shuffle(assignment)
    return assignment[:num_players]

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('create_game')
def handle_create_game(data):
    game_master_id = request.sid
    room_code = generate_room_code()
    
    while room_code in games:
        room_code = generate_room_code()
    
    game = Game(room_code, game_master_id)
    games[room_code] = game
    
    join_room(room_code)
    emit('game_created', {'room_code': room_code})

@socketio.on('join_game')
def handle_join_game(data):
    room_code = data.get('room_code').upper()
    player_name = data.get('player_name')
    player_id = request.sid
    
    if room_code not in games:
        emit('error', {'message': 'Room not found'})
        return
    
    game = games[room_code]
    if player_id in game.players:
        emit('error', {'message': 'Already in game'})
        return
    
    game.players[player_id] = {
        'name': player_name,
        'role': None,
        'sees': [],
        'connected': True
    }
    
    join_room(room_code)
    socketio.emit('player_joined', {
        'players': game.players,
        'room_code': room_code
    }, room=room_code)

@socketio.on('assign_roles')
def handle_assign_roles(data):
    room_code = data.get('room_code')
    active_roles = data.get('roles', [])
    
    if room_code not in games:
        emit('error', {'message': 'Room not found'})
        return
    
    game = games[room_code]
    player_ids = list(game.players.keys())
    num_players = len(player_ids)
    
    if num_players < 6:
        emit('error', {'message': 'Need at least 6 players'})
        return
    
    assigned_roles = assign_roles(num_players, active_roles)
    game.active_roles = active_roles
    
    for player_id, role_key in zip(player_ids, assigned_roles):
        game.role_assignments[player_id] = role_key
    
    game.game_state = 'roles_assigned'
    socketio.emit('roles_assigned', {
        'message': 'Roles assigned. Waiting to reveal...'
    }, room=room_code)

@socketio.on('reveal_roles')
def handle_reveal_roles(data):
    room_code = data.get('room_code')
    
    if room_code not in games:
        emit('error', {'message': 'Room not found'})
        return
    
    game = games[room_code]
    game.game_state = 'reveal_roles'
    
    player_views = {}
    
    for player_id, role_key in game.role_assignments.items():
        player_name = game.players[player_id]['name']
        
        if role_key in ROLES['LOYALISTS']:
            role_data = ROLES['LOYALISTS'][role_key]
        else:
            role_data = ROLES['SPIES'][role_key]
        
        role_display = {
            'role_name': role_data['name'],
            'description': role_data['description'],
            'type': 'Loyalist' if role_data['type'] == 'loyalist' else 'Spy'
        }
        
        sees = role_data['sees']
        special_info = {}
        
        if sees == 'all_spies_except_morgane':
            spy_names = []
            for pid, rid in game.role_assignments.items():
                if rid in ROLES['SPIES'] and rid != 'morgane':
                    spy_names.append(game.players[pid]['name'])
            special_info['sees_spies'] = spy_names
        
        elif sees == 'merlin_and_morgane':
            names = []
            for pid, rid in game.role_assignments.items():
                if rid == 'merlin' or rid == 'morgane':
                    names.append(game.players[pid]['name'])
            special_info['sees_names'] = names
        
        elif sees == 'merlin_only':
            for pid, rid in game.role_assignments.items():
                if rid == 'merlin':
                    special_info['sees_merlin'] = game.players[pid]['name']
        
        elif sees == 'iseult_only':
            for pid, rid in game.role_assignments.items():
                if rid == 'iseult':
                    special_info['sees_iseult'] = game.players[pid]['name']
        
        elif sees == 'tristan_only':
            for pid, rid in game.role_assignments.items():
                if rid == 'tristan':
                    special_info['sees_tristan'] = game.players[pid]['name']
        
        elif sees == 'all_spies':
            spy_names = []
            for pid, rid in game.role_assignments.items():
                if rid in ROLES['SPIES']:
                    spy_names.append(game.players[pid]['name'])
            special_info['sees_spies'] = spy_names
        
        player_views[player_id] = {
            'role': role_display,
            'special_info': special_info,
            'is_gm': player_id == game.game_master_id
        }
    
    socketio.emit('reveal_roles_10s', {
        'player_views': player_views,
        'duration': 10
    }, room=room_code)

@socketio.on('propose_team')
def handle_propose_team(data):
    room_code = data.get('room_code')
    team_players = data.get('team')
    
    if room_code not in games:
        emit('error', {'message': 'Room not found'})
        return
    
    game = games[room_code]
    game.current_team = team_players
    game.team_proposal_by = request.sid
    
    team_names = [game.players[pid]['name'] for pid in team_players]
    socketio.emit('team_proposed', {
        'team': team_names,
        'proposed_by': game.players[request.sid]['name']
    }, room=room_code)

@socketio.on('vote_team')
def handle_vote_team(data):
    room_code = data.get('room_code')
    vote = data.get('vote')
    
    if room_code not in games:
        emit('error', {'message': 'Room not found'})
        return
    
    game = games[room_code]
    game.quest_votes[request.sid] = vote

@socketio.on('end_quest_voting')
def handle_end_quest_voting(data):
    room_code = data.get('room_code')
    
    if room_code not in games:
        emit('error', {'message': 'Room not found'})
        return
    
    game = games[room_code]
    votes = list(game.quest_votes.values())
    approved = votes.count(True) > votes.count(False)
    
    socketio.emit('quest_vote_result', {
        'approved': approved,
        'votes': votes
    }, room=room_code)
    
    game.quest_votes = {}

@socketio.on('quest_mission_votes')
def handle_quest_mission_votes(data):
    room_code = data.get('room_code')
    quest_num = data.get('quest_num')
    player_id = request.sid
    vote = data.get('vote')
    
    if room_code not in games:
        emit('error', {'message': 'Room not found'})
        return
    
    game = games[room_code]
    if 'mission_votes' not in vars(game):
        game.mission_votes = {}
    
    game.mission_votes[player_id] = vote

@socketio.on('end_quest_mission')
def handle_end_quest_mission(data):
    room_code = data.get('room_code')
    quest_num = data.get('quest_num')
    
    if room_code not in games:
        emit('error', {'message': 'Room not found'})
        return
    
    game = games[room_code]
    
    votes = list(game.mission_votes.values())
    sabotages = votes.count(False)
    
    quest_sizes = [0, 3, 4, 4, 5, 5]
    team_size = quest_sizes[quest_num] if quest_num < len(quest_sizes) else 5
    
    if len(game.players) <= 10:
        sabotages_needed = 1
    else:
        sabotages_needed = 2 if quest_num in [4, 5] else 1
    
    quest_succeeds = sabotages < sabotages_needed
    
    game.quest_results.append(quest_succeeds)
    game.current_quest = quest_num
    
    socketio.emit('quest_result', {
        'quest_num': quest_num,
        'succeeds': quest_succeeds,
        'sabotages': sabotages,
        'total_votes': len(votes)
    }, room=room_code)
    
    game.mission_votes = {}

@socketio.on('get_game_state')
def handle_get_game_state(data):
    room_code = data.get('room_code')
    
    if room_code not in games:
        emit('error', {'message': 'Room not found'})
        return
    
    game = games[room_code]
    emit('game_state', game.to_dict())

@socketio.on('disconnect')
def handle_disconnect():
    for room_code, game in games.items():
        if request.sid in game.players:
            game.players[request.sid]['connected'] = False
            socketio.emit('player_disconnected', {
                'player_name': game.players[request.sid]['name']
            }, room=room_code)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
