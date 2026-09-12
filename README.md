# Mini Store Manager

Application web de gestion pour un petit commerce local : produits, clients, commandes et analyses de ventes, développée dans le cadre du projet "Advanced SQL Development Project" (MCS DE1).

## Objectif

Cette application permet à un petit commerce de gérer son catalogue de produits, sa base clients, ses commandes, et de consulter des indicateurs de vente calculés directement via des requêtes SQL sur une base SQLite. Elle a été développée pour démontrer la conception d'une base de données relationnelle, l'écriture de requêtes SQL (jointures, agrégations, sous-requêtes, CTE) et le développement d'une application backend complète.

## Technologies utilisées

- **Backend** : Python 3 / Flask
- **Base de données** : SQLite
- **Frontend** : templates Jinja2 (server-side) + Bootstrap 5 (CDN)
- **Driver base de données** : module `sqlite3` natif de Python (requêtes SQL brutes, paramétrées)

## Structure du projet
mini-store-manager/
├── database/
│ ├── schema.sql # structure de la base (5 tables, contraintes, clés)
│ ├── seed.sql # données de test (5 catégories, 20 produits, 12 clients, 25 commandes, 50 lignes de commande)
│ └── store.db # généré à partir des scripts ci-dessus (non versionné)
├── src/
│ ├── app.py # routes Flask et logique métier
│ ├── db.py # connexion à la base SQLite
│ └── templates/ # templates HTML (Jinja2)
├── report/
│ └── report.pdf # rapport du projet
├── requirements.txt
└── README.md


## Installation

Prérequis : Python 3.10+ installé.

```bash
git clone <URL_DU_REPO>
cd mini-store-manager
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Initialisation de la base de données

La base SQLite n'est pas fournie dans le repository (sauf en secours) : elle se recrée à partir des scripts SQL.

```bash
sqlite3 database/store.db < database/schema.sql
sqlite3 database/store.db < database/seed.sql
```

## Lancement de l'application

```bash
cd src
python app.py
```

L'application est accessible sur [http://127.0.0.1:5000](http://127.0.0.1:5000).

## Pages principales

| Page | URL | Description |
|---|---|---|
| Dashboard | `/` | Vue d'ensemble : nombre de produits/clients/commandes, revenu total, produit le plus vendu, 5 dernières commandes |
| Produits | `/products` | Catalogue produits, recherche, filtre par catégorie, tri, CRUD complet, alerte stock bas |
| Clients | `/customers` | Liste des clients (avec et sans commande), recherche, création, vue détail avec historique de commandes |
| Commandes | `/orders` | Liste des commandes, création de commande (transaction : insertion + décrément du stock), vue détail |
| Analytics | `/analytics` | 6 analyses SQL avancées : revenu par catégorie, top 5 clients, produits jamais commandés, commandes au-dessus de la moyenne, stock bas, ventes par mois |

## Points techniques notables

- Toutes les requêtes SQL utilisent des requêtes paramétrées (`?`), aucune concaténation de chaînes avec des entrées utilisateur.
- La création de commande est encapsulée dans une transaction : si une insertion échoue en cours de route, aucune modification n'est appliquée (`commit`/`rollback`).
- Les clés étrangères sont activées explicitement (`PRAGMA foreign_keys = ON`) à chaque connexion.
- Gestion des erreurs : email client dupliqué, valeurs numériques invalides, suppression bloquée par intégrité référentielle, stock insuffisant, ID de ressource inexistant.


## Auteur

Ania Sadoudi 
