# The Resistance: Avalon - Digital Game Master

Une app web complète pour jouer à The Resistance: Avalon avec jusqu'à 15 joueurs. Le Game Master crée une partie, les joueurs rejoignent avec un code, et l'app gère la révélation des rôles, les votes, et la synchronisation en temps réel.

---

## 🎮 Features

✅ **Real-time multiplayer** avec WebSockets (Socket.IO)
✅ **Game Master dashboard** - contrôle complètement le jeu
✅ **Role reveal automatique** - 10 secondes pour voir les infos spéciales
✅ **Support 6-15 joueurs** - composition dynamique
✅ **Tous les rôles Avalon** - Merlin, Perceval, Morgane, Obélix, Mordred, Mignons, etc.
✅ **Compatibilité intelligente** - l'app empêche les combos broken
✅ **Interface responsive** - fonctionne sur desktop et mobile
✅ **Gratuit à déployer** - Render.com, pas de frais

---

## 🚀 Quick Start

### Localement (5 min)

```bash
# 1. Clone/télécharge le projet
cd avalon-app

# 2. Crée un venv
python -m venv venv
source venv/bin/activate  # Mac/Linux
# ou sur Windows: venv\Scripts\activate

# 3. Install deps
pip install -r requirements.txt

# 4. Lance l'app
python app.py

# 5. Ouvre http://localhost:5000 dans le navigateur
```

### Déployer sur Render (gratuit)

1. Push ton code sur GitHub
2. Va sur https://render.com → New Web Service
3. Connecte ton repo GitHub
4. Configure:
   - **Build**: `pip install -r requirements.txt`
   - **Start**: `python app.py`
5. Deploy

L'app sera accessible via une URL publique (ex: `https://avalon-app-xyz.onrender.com`)

---

## 🎯 How to Play

### Game Master

1. **Ouvre l'app** → Clique "I'm Game Master"
2. **Crée une partie** → Clique "Create Game"
3. **Partage le code** avec les joueurs (ex: ABC123)
4. **Sélectionne les rôles** à jouer (Merlin, Morgane, Loyaliste, etc.)
5. **Clique "Assign Roles"** → l'app assigne aléatoirement
6. **Clique "Reveal Roles"** → tout le monde voit son rôle + infos (10 sec)
7. **Contrôle le jeu**:
   - Proposez une équipe pour chaque quête
   - Les joueurs votent OUI/NON
   - L'équipe approuvée fait la quête
   - Les joueurs votent Succès/Sabotage en secret
   - L'app calcule le résultat
8. **5 quêtes totales** → Loyalistes gagnent si 3 réussissent, espions si 3 échouent

### Joueurs

1. **Ouvre l'app** → Clique "Join Game"
2. **Entre le code + nom** (ex: ABC123, "Alice")
3. **Attends le GM** pour distribuer les rôles
4. **Vois ton rôle** pendant 10 sec (incluant infos spéciales si applicable)
5. **Joue**:
   - Débat pour décider qui aller en quête
   - Vote OUI/NON sur l'équipe proposée
   - Si tu es sélectionné, vote Succès/Sabotage en secret
   - Crois ou doute les autres joueurs

---

## 🎲 Roles et Règles

### Loyalistes
- **Merlin** - Sait qui sont les espions (sauf Morgane). But: aider sans se révéler
- **Perceval** - Sait qui sont Merlin ET Morgane (pas qui est qui). But: trouver Merlin
- **Guinevere** - Sait qui est Merlin. But: voter avec logique
- **Loyaliste Vanilla** - Pas d'infos. But: écouter et déduire

### Espions
- **Morgane** - Connaît les autres espions. Merlin la voit pas. But: rester caché
- **Obélix** - Caché. Connaît les espions. But: sabotage sans révéler
- **Mordred** - Ultra-caché. Personne le connaît, il connaît personne. But: chaos total
- **Minions de Morgane** - Connaissent Merlin. But: le démasquer
- **Espion Vanilla** - Connaît les autres espions. But: sabotage

### Règles de Compatibilité (Automatiques)
L'app empêche les combos cassées:
- Si Perceval est activé, Merlin doit être là
- Si Morgane est activée, Merlin doit être là (sinon elle a aucun rôle)
- Minimum 40% loyalistes, 60% espions (équilibre)

---

## 🏗 Architecture Technique

### Backend (Flask + Socket.IO)
```
app.py
├── Game class (gère l'état d'une partie)
├── Role definitions (tous les rôles)
├── assign_roles() (logique d'équilibre)
└── Socket.IO handlers (real-time updates)
```

### Frontend (HTML/CSS/JS)
```
templates/index.html (structure)
static/
├── style.css (design)
└── script.js (UI logic + Socket.IO)
```

### Real-time Communication
- **Socket.IO** - WebSockets pour les mises à jour instantanées
- Les joueurs voient les changements quasiment en temps réel
- Le GM peut contrôler le tempo du jeu

### Data Flow

```
GM crée partie
  ↓
Joueurs rejoignent avec code
  ↓
GM sélectionne rôles + clique "Assign"
  ↓
App assigne les rôles (aléatoire + équilibré)
  ↓
GM clique "Reveal Roles"
  ↓
Chaque joueur voit:
  - Son rôle immédiatement
  - Ses infos spéciales (10 sec)
  - Puis juste le rôle
  ↓
Quête 1: GM propose équipe → Joueurs votent → Équipe en mission → Votes secrets → Résultat
  ↓
Quêtes 2-5: Même processus
  ↓
Résultat final: Loyalistes (3 réussies) ou Espions (3 échouées)
```

---

## ⚙ Configuration & Customization

### Changer les nombres de joueurs min/max
Dans `app.py`, fonction `assign_roles()`:
```python
if num_players < 6:  # Change 6 à ton min
    emit('error', {'message': 'Need at least X players'})
```

### Ajouter des rôles personnalisés
Dans `app.py`, dictionnaire `ROLES`:
```python
'mon_role': {
    'name': 'Mon Rôle',
    'type': 'loyalist',  # ou 'spy'
    'description': 'Description',
    'sees': 'all_spies'  # ou autre logique
}
```

### Changer les timings
- **Reveal roles**: 10 secondes en dur. Change dans `script.js`:
  ```javascript
  setTimeout(() => { ... }, 10000);  // 10000 = 10 sec
  ```
- **Quest team size**: Dans `app.py`:
  ```python
  quest_sizes = [0, 3, 4, 4, 5, 5]  # Par quête
  ```

---

## 🐛 Troubleshooting

| Problème | Solution |
|----------|----------|
| "Module not found" | Vérifie venv activé + `pip install -r requirements.txt` |
| Socket.IO ne connecte pas | Regarde console du navigateur (F12), cherche erreurs |
| Joueurs ne reçoivent pas les mises à jour | Vérifie que app.py run sans erreurs |
| L'app plante après deploy | Check les logs Render (voir dashboard) |
| Code room pas partagé correctement | Le GM doit copier le code affichér à l'écran |

---

## 📱 Responsive Design

L'app fonctionne sur:
- 🖥 Desktop (optimisé)
- 📱 Tablet (réduit bien)
- 📵 Mobile (portrait et landscape)

---

## 🔒 Sécurité & Privacy

- **Stateless** - aucune donnée persistée (tout disparaît quand le serveur redémarre)
- **No accounts** - pas de login, juste des codes de room aléatoires
- **No database** - tout en mémoire RAM
- **Codes aléatoires** - 6 caractères, difficiles à deviner

**Important**: Cette app est pour jouer entre amis. C'est pas pour des tournois compétitifs.

---

## 🚧 Roadmap (Future Features)

- [ ] Persistance (PostgreSQL)
- [ ] User accounts + friend lists
- [ ] Game history + analytics
- [ ] Custom rules editor
- [ ] Spectator mode
- [ ] AI players (pour tester)
- [ ] Mobile app native (React Native)
- [ ] Voice chat intégrée
- [ ] Tournaments system

---

## 📝 Notes pour le Développement

### Code Style
- Python: PEP 8
- JavaScript: ES6+
- HTML/CSS: BEM methodology (optionnel)

### Testing
Pour tester en local:
1. Ouvre 2+ navigateurs en incognito
2. Un comme GM, les autres comme joueurs
3. Teste le flux complet

### Debugging
- **Backend**: Regarde le terminal où app.py run (logs Socket.IO)
- **Frontend**: F12 → Console (erreurs JS)
- **Network**: F12 → Network tab (requêtes Socket.IO)

---

## 📄 License

MIT - Fais ce que tu veux avec le code.

---

## ❓ FAQ

**Q: Ça marche en offline?**
A: Non, c'est une app web. Besoin d'internet.

**Q: Combien de parties peuvent run simultanément?**
A: Dépend du serveur. Sur Render (gratuit), probablement 10-20. Scale si tu veux.

**Q: Les rôles sont vraiment aléatoires?**
A: Oui, `random.shuffle()`. Pas de bias.

**Q: Comment je triche pas comme GM?**
A: Tu peux voir tout, donc techniquement tu peux. Mais c'est plus fun honnêtement. Honor system.

**Q: Ça marche en français?**
A: L'interface est en anglais pour l'instant, mais tu peux traduire. Tu veux une version FR?

---

Bon jeu! 🎭
