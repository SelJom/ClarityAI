# Clarity Journal API Documentation

## Vue d'ensemble
API REST pour l'application Clarity Journal permettant la gestion des journaux personnels, des utilisateurs et des insights.

## Base URL
```
https://proxy-clarity.gentleocean-eb3ee6eb.westus2.azurecontainerapps.io/
```
## Docs URL
```
https://proxy-clarity.gentleocean-eb3ee6eb.westus2.azurecontainerapps.io/docs
```

## Authentification
Non implémentée dans la version actuelle.

## Routes disponibles

### 👤 Utilisateurs

#### `GET /users`
Liste tous les utilisateurs.
- **Réponse**: Liste de `UserOut`

#### `POST /users`
Crée un nouvel utilisateur.
- **Corps**: `UserCreate`
  ```json
  {
    "email": "user@example.com",
    "password": "string",
    "role": "user|pro",
    "full_name": "string"
  }
  ```
- **Réponse**: `UserOut`

#### `GET /users/{user_id}`
Récupère un utilisateur par son ID.
- **Réponse**: `UserOut`

#### `PUT /users/{user_id}`
Met à jour un utilisateur.
- **Corps**: `UserUpdate` (tous les champs optionnels)
- **Réponse**: `UserOut`

#### `DELETE /users/{user_id}`
Supprime un utilisateur.

### 📓 Journaux

#### `GET /journals`
Liste les journaux.
- **Paramètres**: `user_id` (optionnel)
- **Réponse**: Liste de `JournalOut`

#### `POST /journals`
Crée un nouveau journal.
- **Corps**: `JournalCreate`
  ```json
  {
    "user_id": 0,
    "title": "string"
  }
  ```
- **Réponse**: `JournalOut`

#### `GET /journals/{journal_id}`
Récupère un journal par son ID.
- **Réponse**: `JournalOut`

#### `PUT /journals/{journal_id}`
Met à jour un journal.
- **Corps**: `JournalUpdate`
- **Réponse**: `JournalOut`

#### `DELETE /journals/{journal_id}`
Supprime un journal.

### 📄 Pages de journal

#### `GET /journals/{journal_id}/pages`
Liste les pages d'un journal.
- **Réponse**: Liste de `JournalPageOut`

#### `POST /journals/{journal_id}/pages`
Crée une nouvelle page.
- **Corps**: `JournalPageCreate`
  ```json
  {
    "journal_id": 0,
    "page_number": 0,
    "content": "string",
    "mood": 0,
    "entry_type": "text"
  }
  ```
- **Réponse**: `JournalPageOut`

#### `GET /journal_pages/{page_id}`
Récupère une page par son ID.
- **Réponse**: `JournalPageOut`

#### `PUT /journal_pages/{page_id}`
Met à jour une page.
- **Corps**: `JournalPageUpdate`
- **Réponse**: `JournalPageOut`

#### `DELETE /journal_pages/{page_id}`
Supprime une page.

#### `GET /journal_pages`
Liste toutes les pages.
- **Réponse**: Liste de `JournalPageOut`

### 🔐 Sessions

#### `GET /sessions`
Liste toutes les sessions.
- **Réponse**: Liste de `SessionOut`

#### `POST /sessions`
Crée une nouvelle session.
- **Corps**: `SessionCreate`
  ```json
  {
    "user_id": 0,
    "session_token": "string",
    "expires_at": "string"
  }
  ```
- **Réponse**: `SessionOut`

#### `GET /sessions/{session_token}`
Récupère une session par son token.
- **Réponse**: `SessionOut`

#### `DELETE /sessions/{session_token}`
Supprime une session.

### 👩‍⚕️ Permissions

#### `GET /permissions`
Liste toutes les permissions.
- **Réponse**: Liste de `PermissionOut`

#### `POST /permissions`
Accorde une nouvelle permission.
- **Corps**: `PermissionCreate`
  ```json
  {
    "user_id": 0,
    "professional_id": 0,
    "journal_id": 0,
    "can_view": true,
    "can_comment": false
  }
  ```
- **Réponse**: `PermissionOut`

#### `GET /permissions/{permission_id}`
Récupère une permission par son ID.
- **Réponse**: `PermissionOut`

#### `DELETE /permissions/{permission_id}`
Révoque une permission.

### 💡 Insights

#### `GET /insights`
Liste tous les insights.
- **Réponse**: Liste de `InsightOut`

#### `POST /insights`
Crée un nouvel insight.
- **Corps**: `InsightCreate`
  ```json
  {
    "journal_id": 0,
    "journal_page_id": 0,
    "summary": "string",
    "sentiment_score": 0,
    "emotion_tags": {}
  }
  ```
- **Réponse**: `InsightOut`

#### `GET /insights/{insight_id}`
Récupère un insight par son ID.
- **Réponse**: `InsightOut`

#### `PUT /insights/{insight_id}`
Met à jour un insight.
- **Corps**: `InsightCreate`
- **Réponse**: `InsightOut`

#### `DELETE /insights/{insight_id}`
Supprime un insight.

#### `GET /journals/{journal_id}/insights`
Liste les insights d'un journal.
- **Réponse**: Liste de `InsightOut`

## Modèles de données

### UserOut
```json
{
  "email": "string",
  "role": "string",
  "full_name": "string",
  "id": 0,
  "created_at": "string",
  "updated_at": "string"
}
```

### JournalOut
```json
{
  "user_id": 0,
  "title": "string",
  "id": 0,
  "created_at": "string",
  "updated_at": "string"
}
```

### JournalPageOut
```json
{
  "journal_id": 0,
  "page_number": 0,
  "content": "string",
  "mood": 0,
  "entry_type": "string",
  "id": 0,
  "created_at": "string",
  "updated_at": "string"
}
```

### SessionOut
```json
{
  "user_id": 0,
  "session_token": "string",
  "expires_at": "string",
  "id": 0,
  "created_at": "string",
  "last_active": "string"
}
```

### PermissionOut
```json
{
  "user_id": 0,
  "professional_id": 0,
  "journal_id": 0,
  "can_view": true,
  "can_comment": false,
  "id": 0,
  "created_at": "string"
}
```

### InsightOut
```json
{
  "journal_id": 0,
  "journal_page_id": 0,
  "summary": "string",
  "sentiment_score": 0,
  "emotion_tags": {},
  "id": 0,
  "created_at": "string"
}

```
