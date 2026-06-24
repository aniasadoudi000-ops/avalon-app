from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import secrets
import random
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
socketio = SocketIO(app, cors_allowed_origins="*")

games = {}

ROLES = {
    'loyalists': {
        'merlin': {
            'name': 'Merlin',
            'type': 'loyalist',
            'description': 'Sait qui sont TOUS les espions sauf Morgane',
            'sees': 'all_spies_except_morgane'
        },
        'perceval': {
            'name': 'Perceval',
            'type': 'loyalist',
            'description': 'Sait qui sont Merlin ET Morgane, mais pas qui est qui',
            'sees': 'merlin_and_morgane'
        },
        'guinevere': {
            'name': 'Guinevere',
            'type': 'loyalist',
            'description': 'Sait qui est Merlin',
            'sees': 'merlin_only'
        },
        'tristan': {
            'name': 'Tristan',
            'type': 'loyalist',
            'description': 'Sait qui est Iseult',
            'sees': 'iseult_only'
        },
        'iseult': {
            'name': 'Iseult',
            'type': 'loyalist',
            'description': 'Sait qui est Tristan',
            'sees': 'tristan_only'
        },
        'vivien': {
            'name': 'Vivien',
            'type': 'loyalist',
            'description': 'Loyaliste qui sait qui est Merlin',
            'sees': 'merlin_only'
        },
        'loyal_servant': {
            'name': 'Loyal Servant',
            'type': 'loyalist',
            'description': 'Loyaliste vanilla - pas d\'infos spéciales',
            'sees': 'nothing'
        }
    },
    'spies': {
        'morgane': {
            'name': 'Morgane',
            'type': 'spy',
            'description': 'Espion. Connaît tous les autres espions. Trompe Merlin',
            'sees': 'all_spies'
        },
        'oberon': {
            'name': 'Oberon',
            'type': 'spy',
            'description': 'Espion caché. Connaît tous les autres espions',
            'sees': 'all_spies'
        },
        'mordred': {
            'name': 'Mordred',
            'type': 'spy',
            'description': 'Espion ultra-caché. Personne le connaît, il connaît personne',
            'sees': 'nothing'
        },
        'minions': {
            'name': 'Minion de Morgane',
            'type': 'spy',
            'description': 'Espion qui connaît Merlin et essaie de le démasquer',
            'sees': 'merlin_only'
        },
        'lancelot': {
            'name': 'Lancelot (Traître)',
            'type': 'spy',
            'description': 'Espion qui prétend être loyal',
            'sees': 'all_spies'
        },
        'minion': {
            'name': 'Minion',
            'type': 'spy',
            'description': 'Espion vanilla',
            'sees': 'all_spies'
        }
    }
}

COMPATIBILITY = {
    'merlin': {'requires': ['morgane'], 'blocks': []},
    'perceval': {'requires': ['merlin'], 'blocks': []},
    'morgane': {'requires': [], 'blocks': []},
    'minions': {'requires': ['morgane'], 'blocks': []},
    'oberon': {'requires': [], 'blocks': []},
    'mordred': {'requires': [], 'blocks': []},
    'guinevere': {'requires': ['merlin'], 'blocks': []},
    'tristan': {'requires': ['iseult'], 'blocks': []},
    'iseult': {'requires': ['tristan'], 'blocks': []},
    'lancelot': {'requires': [], 'blocks': []},
    'vivien': {'requires': ['merlin'], 'blocks': []},
    'loyal_servant': {'requires': [], 'blocks': []},
    'minion': {'requires': [], 'blocks': []}
}

class Game:
    def __init__(self, room_code, game_master_id):
        self.room_code = room_code
        self.game_master_id = game_master_id
        self.players = {}
        self.game_state = 'waiting'
        self.selected_roles = []
        self.role_assignments = {}
        self.current_quest = 0
        self.quest_results = []
        self.quest_votes = {}
        self.mission_votes = {}
        self.current_team = []

    def to_dict(self):
        return {
            'room_code': self.room_code,
            'game_master_id': self.game_master_id,
            'players': self.players,
            'game_state': self.game_state,
            'selected_roles': self.selected_roles,
            'role_assignments': self.role_assignments,
            'current_quest': self.current_quest,
            'quest_results': self.quest_results
        }

def generate_room_code():
    return ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))

def get_compatible_roles(selected_roles):
    compatible = {}
    all_roles = {**ROLES['loyalists'], **ROLES['spies']}
    
    for role_key, role_data in all_roles.items():
        if role_key in selected_roles:
            compatible[role_key] = {'enabled': True, 'reason': 'selected'}
        else:
            reqs = COMPATIBILITY.get(role_key, {}).get('requires', [])
            blocks = COMPATIBILITY.get(role_key, {}).get('blocks', [])
            
            req_satisfied = all(req in selected_roles for req in reqs)
            not_blocked = not any(block in selected_roles for block in blocks)
            
            if req_satisfied and not_blocked:
                compatible[role_key] = {'enabled': True, 'reason': ''}
            else:
                reason = f"Requires: {', '.join(reqs)}" if not req_satisfied else f"Blocked by: {', '.join(blocks)}"
                compatible[role_key] = {'enabled': False, 'reason': reason}
    
    return compatible

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
    room_code = data.get('room_code', '').upper()
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
        'connected': True
    }
    
    join_room(room_code)
    socketio.emit('player_joined', {
        'players': game.players,
        'room_code': room_code
    }, room=room_code)

@socketio.on('get_compatible_roles')
def handle_get_compatible_roles(data):
    room_code = data.get('room_code')
    
    if room_code not in games:
        emit('error', {'message': 'Room not found'})
        return
    
    game = games[room_code]
    compatible = get_compatible_roles(game.selected_roles)
    
    roles_list = []
    for role_key, role_data in {**ROLES['loyalists'], **ROLES['spies']}.items():
        role_type = 'loyalist' if role_key in ROLES['loyalists'] else 'spy'
        compat_info = compatible[role_key]
        
        roles_list.append({
            'key': role_key,
            'name': role_data['name'],
            'type': role_type,
            'description': role_data['description'],
            'enabled': compat_info['enabled'],
            'reason': compat_info['reason'],
            'selected': role_key in game.selected_roles
        })
    
    emit('compatible_roles', {'roles': roles_list})

@socketio.on('toggle_role')
def handle_toggle_role(data):
    room_code = data.get('room_code')
    role_key = data.get('role_key')
    
    if room_code not in games:
        emit('error', {'message': 'Room not found'})
        return
    
    game = games[room_code]
    
    if role_key in game.selected_roles:
        game.selected_roles.remove(role_key)
    else:
        game.selected_roles.append(role_key)
    
    socketio.emit('roles_updated', {
        'selected_roles': game.selected_roles
    }, room=room_code)

@socketio.on('start_assignment')
def handle_start_assignment(data):
    room_code = data.get('room_code')
    
    if room_code not in games:
        emit('error', {'message': 'Room not found'})
        return
    
    game = games[room_code]
    game.game_state = 'assigning_roles'
    
    players_list = []
    for player_id, player in game.players.items():
        players_list.append({
            'id': player_id,
            'name': player['name']
        })
    
    socketio.emit('ready_to_assign', {
        'players': players_list,
        'available_roles': game.selected_roles
    }, room=room_code)

@socketio.on('assign_player_role')
def handle_assign_player_role(data):
    room_code = data.get('room_code')
    player_id = data.get('player_id')
    role_key = data.get('role_key')
    
    if room_code not in games:
        emit('error', {'message': 'Room not found'})
        return
    
    game = games[room_code]
    game.role_assignments[player_id] = role_key

@socketio.on('confirm_assignments')
def handle_confirm_assignments(data):
    room_code = data.get('room_code')
    
    if room_code not in games:
        emit('error', {'message': 'Room not found'})
        return
    
    game = games[room_code]
    
    if len(game.role_assignments) != len(game.players):
        emit('error', {'message': 'Not all players assigned'})
        return
    
    game.game_state = 'roles_assigned'
    socketio.emit('assignments_confirmed', {
        'message': 'Roles assigned! Ready to reveal.'
    }, room=room_code)

@socketio.on('reveal_roles')
def handle_reveal_roles(data):
    room_code = data.get('room_code')
    
    if room_code not in games:
        emit('error', {'message': 'Room not found'})
        return
    
    game = games[room_code]
    game.game_state = 'roles_revealed'
    
    player_views = {}
    
    for player_id, role_key in game.role_assignments.items():
        if role_key in ROLES['loyalists']:
            role_data = ROLES['loyalists'][role_key]
        else:
            role_data = ROLES['spies'][role_key]
        
        role_display = {
            'role_name': role_data['name'],
            'description': role_data['description'],
            'type': 'Loyalist' if role_data['type'] == 'loyalist' else 'Spy'
        }
        
        special_info = {}
        sees = role_data['sees']
        
        if sees == 'all_spies_except_morgane':
            spy_names = []
            for pid, rid in game.role_assignments.items():
                if rid in ROLES['spies'] and rid != 'morgane':
                    spy_names.append(game.players[pid]['name'])
            special_info['type'] = 'spies'
            special_info['names'] = spy_names
        
        elif sees == 'merlin_and_morgane':
            names = []
            for pid, rid in game.role_assignments.items():
                if rid == 'merlin' or rid == 'morgane':
                    names.append(game.players[pid]['name'])
            special_info['type'] = 'two_names'
            special_info['names'] = names
        
        elif sees == 'merlin_only':
            for pid, rid in game.role_assignments.items():
                if rid == 'merlin':
                    special_info['type'] = 'one_name'
                    special_info['name'] = game.players[pid]['name']
        
        elif sees == 'iseult_only':
            for pid, rid in game.role_assignments.items():
                if rid == 'iseult':
                    special_info['type'] = 'one_name'
                    special_info['name'] = game.players[pid]['name']
        
        elif sees == 'tristan_only':
            for pid, rid in game.role_assignments.items():
                if rid == 'tristan':
                    special_info['type'] = 'one_name'
                    special_info['name'] = game.players[pid]['name']
        
        elif sees == 'all_spies':
            spy_names = []
            for pid, rid in game.role_assignments.items():
                if rid in ROLES['spies']:
                    spy_names.append(game.players[pid]['name'])
            special_info['type'] = 'spies'
            special_info['names'] = spy_names
        
        player_views[player_id] = {
            'role': role_display,
            'special_info': special_info
        }
    
    socketio.emit('reveal_roles_10s', {
        'player_views': player_views,
        'duration': 10
    }, room=room_code)

@socketio.on('disconnect')
def handle_disconnect():
    for room_code, game in list(games.items()):
        if request.sid in game.players:
            game.players[request.sid]['connected'] = False

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
