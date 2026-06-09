
# Résumé du problème pour reprise dans une autre session

## Contexte

Branche `org_edito_blocs`. La PR ajoute un champ `blocs` au modèle `Organization` :
```python
# udata/core/organization/models.py
from udata.core.edito_blocs.models import Bloc

@generate_fields(read_mask_exclude=["blocs"])
class Organization(...):
    ...
    blocs = field(EmbeddedDocumentListField(Bloc), generic=True)
```

## Le cycle d'imports introduit

L'ajout de l'import top-level `from udata.core.edito_blocs.models import Bloc` dans `organization/models.py` ferme le cycle suivant :

```
organization/models.py
  → edito_blocs/models.py        (importe Dataservice, dataset_fields, Reuse au top-level)
    → dataservices/models.py
      → dataset/api_fields.py
        → organization/models.py  (cycle : Organization pas encore défini)
```

Le nœud structurel : `dataset/api_fields.py:6` importe `Organization` au top-level pour utiliser `Organization.__ref_fields__` aux lignes 240 et 389 (deux `fields.Nested(Organization.__ref_fields__, ...)` dans `community_resource_fields` et `dataset_fields`).

Avant cette PR, le cycle était dormant : `organization/models.py` ne touchait pas à `edito_blocs/models.py`, donc le chargement passait dans l'ordre `organization → dataset → dataservices → reuse → site → post`, et `Post`/`Site` (qui importent `Bloc`) étaient chargés après que tous les modèles dont dépend `edito_blocs/models.py` soient prêts.

## Tentative de fix (partielle) déjà appliquée sur la branche

Refactor "base.py" : extraction de la classe `Bloc` dans `udata/core/edito_blocs/base.py` (sans dépendances cycliques). Tous les imports de `Bloc` ont été migrés vers ce module :
- `organization/models.py` → `from udata.core.edito_blocs.base import Bloc`
- `post/models.py` → idem
- `site/models.py` → idem (`SITE_BLOCS_FIELDS` reste sur `models.py`)

**Ça casse le cycle**, mais **régresse le swagger**.

## La régression de swagger (non résolue)

Le mécanisme `generic=True` sur `EmbeddedDocumentListField(Bloc)` s'appuie sur une découverte dynamique des sous-classes :

```python
# udata/api_fields.py:207-228
allowed_classes = (
    classes_by_parents[field.field.document_type_obj]
    if ... and field.field.document_type_obj in classes_by_parents
    else set()
)
if generic and allowed_classes:
    # un GenericField listant {MarkdownBloc, DatasetsListBloc, ...}
else:
    # fallback : Nested(Bloc) plat → uniquement {id}
```

`classes_by_parents[Bloc]` est rempli par `save_class_by_parents(cls)` à chaque `@generate_fields()` sur une sous-classe de `Bloc`. Donc les sous-classes ne sont enregistrées qu'**à l'import** du module qui les définit (`edito_blocs/models.py`).

Avec le refactor `base.py` :
- `organization/models.py` (ligne 11 dans `udata/models/__init__.py`) importe `Bloc` depuis `base.py` mais **n'importe pas `edito_blocs/models.py`**.
- Au moment où `@generate_fields()` décore `Organization`, `classes_by_parents[Bloc]` est **vide**.
- Conséquence : `Organization.blocs` tombe dans le fallback. Le swagger n'expose que `Bloc.__read_fields__ = {id}` au lieu de la liste polymorphique des sous-classes.

Site et Post ne souffrent pas du problème : ils sont chargés après `edito_blocs/models.py` (Site l'importe pour `SITE_BLOCS_FIELDS`), donc le registre est rempli avant leur décoration.

## Mise à jour — review (2026-05-21)

Confirmation par lecture du code, avec trois précisions absentes de l'analyse ci-dessus :

1. **Ce n'est pas qu'une régression de swagger : c'est une régression de la sérialisation runtime.** `Organization.__read_fields__` sert à la fois à la doc OpenAPI **et** au `@api.marshal_with(Organization.__read_fields__)` de `OrganizationAPI.get`/`put`. Le fallback `Nested(Bloc) = {id}` casse donc la **vraie réponse API** : `GET /api/1/organizations/<id>/?X-Fields={*}` renvoie `"blocs": [{"id": …}]`, sans `class`/`title`/`content`.

2. **C'est le bloqueur CI actuel.** `test_blocs_returned_with_x_fields` (`test_organizations_api.py`) lève un `KeyError` sur `response.json["blocs"][0]["class"]`. Les deux jobs CI échouent (Python 3.11 et 3.13), `dist` reste `not_run`. À l'inverse l'**écriture** fonctionne (`patch()` résout les classes via `classes_by_names` au runtime, quand tout est enregistré) — d'où le passage de `test_admin_can_update_blocs`, qui revérifie en base via `org.reload()` et non via l'API. Seule la lecture est cassée.

3. **La régression est structurellement garantie, pas seulement dépendante de l'ordre dans `udata/models/__init__.py`.** Même en important `edito_blocs/models.py` en premier, ses imports top-level (`dataservices.models → dataset/api_fields.py`, cf. cycle ci-dessus) décorent `Organization` **avant** que les sous-classes de `Bloc` — définies plus bas dans le même fichier (lignes 37+) — ne soient enregistrées. `Organization` est donc systématiquement décoré avec `classes_by_parents[Bloc]` vide.

### Pistes de correctif (non triviales, au choix)

- **Résolution paresseuse du `GenericField`** : construire la liste des sous-classes au moment du marshalling plutôt qu'à la décoration (`api_fields.py:207-228`). Corrige tous les champs génériques quel que soit l'ordre d'import, mais touche du code central et partagé.
- **Forcer l'enregistrement avant décoration** : garantir l'import de `edito_blocs/models.py` avant la décoration d'`Organization` sans rouvrir le cycle — délicat, c'est précisément ce que `base.py` cherche à éviter.
- **Modèle blocs explicite** : ne pas passer par `generate_fields`/`generic=True` pour `blocs` et fournir un modèle polymorphe construit à la demande, sur le même principe que `assignments` qui contourne déjà l'enregistrement tardif via un modèle manuel (cf. `organization/models.py:154-155`).

---

# Plan d'implémentation retenu : handle `api_fields()` par classe

Décision : on traite la **cause racine** (construction des modèles figée trop tôt), pas le symptôme
`blocs`. À la place de `@generate_fields` (eager, à la décoration), chaque modèle expose une
`@classmethod api_fields()` **mémoïsée** qui retourne un handle `ApiFields`. Les modèles flask-restx ne
sont construits qu'à l'appel de `.read()` / `.write()` / `.ref()` / `.page()` sur ce handle — donc de
façon **paresseuse**, depuis les modules `*/api.py` qui sont importés *après* tous les modèles.
`classes_by_parents[Bloc]` (et tout le graphe) est alors complet : plus aucune dépendance à l'ordre
d'import.

Bénéfice transverse (objectif « virer flask-restx ») : `ApiFields` est l'abstraction stable. `.read()`
retourne aujourd'hui un `flask_restx.Model`, demain un schéma OpenAPI / un pydantic — on réécrit
l'implémentation du handle, pas les call-sites. La classe Mongo redevient pure : les métadonnées
restent sur les champs via `field()`, le handle vit à côté.

## 1. La forme : `@classmethod api_fields()` mémoïsée

Chaque classe qui a aujourd'hui `@generate_fields(**kwargs)` définit à la place :

```python
class Organization(...):
    @cached_classmethod
    def api_fields(cls):
        return ApiFields(cls, read_mask_exclude=["blocs"])
```

Les classes sans `api_fields()` (modèles non exposés, types externes) tombent sur le comportement
actuel : `nested_fields` explicite requis, sinon `String`.

**Mémoïsation — pourquoi un décorateur maison et pas `@classmethod @functools.cache`.** Deux raisons,
souvent confondues. (1) `functools.cache` n'est **pas** un descripteur (pas de `__get__`) ; empilé sous
`classmethod`, `cls` n'est pas passé correctement — ça n'a jamais bien marché, et ce n'est **pas** lié
au retrait du chaînage `classmethod`+`property` en 3.13 (erreur d'attribution fréquente). (2) Surtout,
`cache`/`lru_cache` attachent le cache à la *fonction*, pas à la classe : cache partagé entre toutes les
sous-classes + référence retenue qui bloque le GC. D'où un mini-décorateur qui cache **par classe** dans
`cls.__dict__` — en testant `attr not in cls.__dict__` et **pas** `hasattr` (qui remonterait la MRO et
ferait réutiliser à `MarkdownBloc` le handle calculé pour `Bloc`) :

```python
def cached_classmethod(fn):
    attr = f"_cached_{fn.__name__}"

    @classmethod
    @functools.wraps(fn)
    def wrapper(cls):
        if attr not in cls.__dict__:        # __dict__, pas hasattr : per-classe, non hérité
            setattr(cls, attr, fn(cls))
        return cls.__dict__[attr]

    return wrapper
```

La mémoïsation n'est pas une optim, elle est **requise pour la correction** : flask-restx indexe les
modèles par nom, et la rupture des cycles (§3) repose sur le fait que le `Nested` référence *le même*
objet `Model` que celui qu'on est en train de remplir. Un handle recréé à chaque appel casse les deux.

## 2. Le handle `ApiFields`

Interface (tout mémoïsé par `(kind, tag)` dans le handle) :

- `.ref()` — modèle minimal (champs `show_as_ref`)
- `.read(tag=None)` — modèle complet, ou variante d'un endpoint (cf. §4)
- `.write(tag=None)`
- `.page(tag=None)` — `pager(read)`
- `.parser()` — ex-`__index_parser__`
- `.apply_sort_filters(qs)` / `.apply_pagination(qs)` — ex-méthodes posées sur la classe

Tout le corps actuel de `generate_fields` (`convert_db_to_field`, les boucles champs/méthodes, la
construction du parser) déménage dans `ApiFields`, appelé à la demande.

## 3. Résolution des références + cycles

Dans `convert_db_to_field`, on remplace la lecture d'attribut figé par l'appel de méthode. Aujourd'hui
(`api_fields.py:293`) :

```python
if nested_fields is None and hasattr(document_type, "__ref_fields__"):
    nested_fields = document_type.__ref_fields__
```

devient :

```python
if nested_fields is None and hasattr(document_type, "api_fields"):
    nested_fields = document_type.api_fields().ref()   # .read() pour les EmbeddedDocument
```

`document_type` est déjà résolu en classe (`db.resolve_model("Organization")`), donc **aucun registre
externe** : la classe *est* le point d'accès à son handle.

**(a) Cycles via références** (`Dataset.organization → Organization → …`) : on les casse par couches —
matérialiser **d'abord tous les `.ref()`** (quasi exclusivement scalaires : id/title/slug), **puis** les
`.read()/.write()/.page()` qui ne référencent les autres modèles que via ces `.ref()` déjà prêts.

**(b) Cycles via embedded génériques** (le piège accordéon : `AccordionListBloc.items →
AccordionItemBloc.content (Bloc générique) → toutes les sous-classes, dont AccordionListBloc → …`) : la
mémoïsation seule ne termine pas. Technique du modèle récursif : au **début** de `.read()`, créer le
`api.model(name, {})` **vide**, le poser dans le cache du handle, **puis** construire les champs (qui
peuvent référencer ce modèle encore vide via `Nested`/`GenericField`), **puis** le remplir. flask-restx
lit le contenu au *marshalling* (requête), donc après remplissage.

⚠️ **Régression de comportement à corriger en même temps.** Aujourd'hui `AccordionItemBloc.content`
n'inclut PAS `AccordionListBloc`/`HeroBloc` — uniquement parce que ces classes sont définies *après*
`AccordionItemBloc` dans `edito_blocs/models.py` (l.122) et ne sont donc pas encore dans
`classes_by_parents[Bloc]` à la décoration. L'ordre d'import encode **par accident** la contrainte
`BLOCS_DISALLOWED_IN_ACCORDION` / `check_no_recursive_blocs`. Avec le registre complet à la résolution,
ce filtrage implicite saute → le rendre **explicite** :

```python
content = field(EmbeddedDocumentListField(Bloc), generic=True,
                excluded_subclasses=BLOCS_DISALLOWED_IN_ACCORDION)
```

(le constructeur générique, `api_fields.py:209-228`, filtre `allowed_classes`). Bonus : corrige aussi
l'incohérence actuelle où `HeroBloc` (défini l.93, avant l.122) *est* dans le schéma de `content` alors
que le runtime l'interdit.

## 4. Tags : unifier mask / card / preview

C'est le gain de la forme handle. Les « légères variations par endpoint » sont aujourd'hui bricolées de
trois façons : `read_mask_exclude=["blocs"]` (Organization), `page_mask_exclude` (Post), et les modèles
« card » dupliqués à la main avec des masques string (`DATASET_CARD_MASK`, `dataset_card_fields`…). Un
seul mécanisme remplace tout :

```python
title = field(StringField(), tags=["card", "preview"])
...
Organization.api_fields().read(tag="card")   # -> api.model("Organization (read:card)", ...)
```

`.read(tag="card")` ne garde que les champs portant ce tag (et mémoïse sous un nom de modèle dédié).
**Limite à poser dès le départ** : le tag ne se propage **pas** aux nested (sinon explosion
combinatoire de modèles nommés) ; chaque nested garde son `.ref()` par défaut. Suffisant pour des
variations légères ; si besoin un jour, tag explicite sur le nested.

## 5. À la déclaration : références, jamais de modèle construit

Le piège qui ne disparaît pas : un `.read()` appelé **au niveau module d'un fichier de modèles** (comme
les `*_card_fields` actuels, `edito_blocs/models.py:26-33`) re-déclenche une construction trop tôt. La
règle : un champ stocke `(handle/classe, tag)`, et c'est la résolution qui appelle `.read(tag=…)`.
Jamais d'appel `.read()`/`.write()`/`.ref()` au niveau module d'un modèle.

## 6. La seule garantie nécessaire : registre complet avant le premier `.read()`

Pas besoin d'une passe qui force la matérialisation de tous les modèles au boot : la paresse fait le
travail, chaque endpoint matérialise ce qu'il consomme depuis les `*/api.py` (chargés après les
modèles). On laisse donc la résolution se faire au fil de l'eau.

**Mais un point n'est pas négociable : tous les modèles doivent être importés avant le premier `.read()`**,
sinon `Bloc.__subclasses__()` est incomplet et on re-fige le bug — cette fois **mémoïsé à vie**. Et la
paresse « naturelle » ne le garantit PAS : dans `api/__init__.py:init_app`, `organization/api.py` est
importé **l.355**, alors que les sous-classes de `Bloc` ne sont chargées que via `site/api.py` →
`site/models.py` → `edito_blocs/models.py`, importé **l.360**. Le décorateur
`@api.marshal_with(Organization.api_fields().read())` s'évalue donc avant l'enregistrement des blocs →
exactement le bug actuel. On ne peut pas parier sur « un module précédent a peut-être déjà importé
`edito_blocs.models` ».

La garantie tient en **une ligne** (pas une passe), en tête de `init_app`, avant les imports d'API :

```python
def init_app(app):
    import udata.models   # noqa — registre complet ; tout .read() ultérieur voit le graphe entier
    import udata.core.access_type.api  # noqa
    ...
```

**Garde fail-fast (recommandée, quasi gratuite).** Un flag passé à `True` juste après ce
`import udata.models` ; `.read()`/`.ref()`/… lèvent une `RuntimeError` si appelés avant. Ça ne force
rien à matérialiser — ça transforme tout futur `.read()` trop précoce (refacto qui déplace un import,
`.read()` au niveau module d'un fichier de modèles…) en **crash explicite au boot** au lieu d'un champ
silencieusement réduit à `{id}`. C'est la pièce qui garantit que le bug ne peut plus réapparaître
silencieusement.

## 7. Call-sites à migrer

- **Modèles** : `@generate_fields(...)` → `def api_fields(cls): return ApiFields(cls, ...)`.
- **Lectures d'attributs** (~30 fichiers, mécanique) : `X.__read_fields__` → `X.api_fields().read()`,
  `X.__ref_fields__` → `.ref()`, `X.__page_fields__` → `.page()`, `X.__write_fields__` → `.write()`,
  `X.__index_parser__` → `.parser()`, `X.apply_sort_filters/apply_pagination` → méthodes du handle.
  Les accès dans les `*/api.py` s'exécutent après la passe → OK une fois renommés.
- **Modèles dérivés construits à l'import** (à transformer en `(handle, tag)`, §5), repérés par
  `rg "api\.model\(|api\.inherit\(" + rg "__(read|write|ref|page)_fields__"` :
  - `edito_blocs/models.py:26-33` — `dataset_card_fields` / `reuse_card_fields` / `dataservice_card_fields` → `tag="card"` ;
  - `core/dataset/api_fields.py` — `dataset_fields`, `community_resource_fields` ;
  - `core/organization/api_fields.py`, `core/user/api_fields.py`, `core/reuse/api_fields.py`, `core/spatial/api_fields.py` ;
  - `core/dataservices/models.py`, `core/organization/models.py`, `core/visualizations/models.py`.
  Audit : ne migrer que ceux qui **lisent un champ généré d'un autre modèle** ; les `api.model`
  « feuilles » (champs littéraux) peuvent rester eager.

## 8. Étapes ordonnées

1. Introduire `ApiFields` + `cached_classmethod`, et migrer **une** classe pilote (`Organization`) vers
   `api_fields()`, en gardant `@generate_fields` partout ailleurs (coexistence : `convert_db_to_field`
   tente `api_fields()` puis retombe sur `__ref_fields__`).
2. Placeholders pour cycles (§3b) + ordre ref → read (§3a).
3. `excluded_subclasses` sur `AccordionItemBloc.content` (§3) ; vérifier le schéma des accordéons.
4. Tags (§4) : porter `read_mask_exclude`/`page_mask_exclude`/les « card » sur `tags=` + `.read(tag=…)`.
5. Migrer le reste des modèles + tous les call-sites (§7), un module à la fois ; la garde fail-fast (en
   `warning` pendant la migration) signale les `.read()` trop précoces restants.
6. Passer la garde en `raise`, supprimer `@generate_fields` et les attributs `__*_fields__`.

## 9. Tests

- `test_blocs_returned_with_x_fields` passe **sans** dépendre de l'ordre d'import.
- Graphe générique cyclique : sérialiser un `AccordionListBloc` imbriqué → (a) le marshalling termine,
  (b) `AccordionListBloc`/`HeroBloc` absents du schéma de `content`.
- Tags : `.read(tag="card")` ne renvoie que les champs taggués ; `.read()` les renvoie tous.
- Fail-fast : accès à `api_fields().read()` avant `import udata.models` (registre incomplet) →
  `RuntimeError` (logique non triviale → test unitaire justifié).
- Non-régression swagger : comparer `/api/1/swagger.json` avant/après sur Dataset, Organization, Reuse.