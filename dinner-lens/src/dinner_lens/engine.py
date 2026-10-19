"""Rule-based eligibility, editorial ordering, vector continuation and signed cursors."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import time
from collections import Counter
from dataclasses import dataclass
from typing import Any

from .data import Knowledge, canonical, digest, known_number, normalize, predicate
from .embeddings import EmbeddingIndex

RANKING_VERSION = "curated-first-lexicographic-v4-compositional-guards"
MAX_FILTER_BYTES = 128 * 1024
MAX_CONTEXT_BYTES = 512 * 1024
COLORS = {"red", "white", "rose", "orange"}
SWEETNESS = {"dry", "semi_dry", "semi_sweet", "sweet", "brut", "extra_brut", "brut_nature"}
KINDS = {"still", "sparkling"}
FILTERS = {"color", "sweetness", "wine_kind", "exclude_producer", "exclude_producers", "seen_wine_slugs", "rejected_wine_slugs", "restaurant_wine_slugs", "grapes_include", "grapes_exclude", "max_alcohol_percent", "max_price_rub", "max_sugar_g_l", "in_stock"}
LIST_FILTERS = {"exclude_producers", "seen_wine_slugs", "rejected_wine_slugs", "restaurant_wine_slugs", "grapes_include", "grapes_exclude"}
ATTRIBUTES = {"heat": {"none", "low", "medium", "high"}, "acidity": {"low", "medium", "high"}, "sauce_sweetness": {"none", "low", "medium", "high"}, "protein_family": {"meat", "fish", "seafood", "poultry", "game", "vegetarian"}, "poultry_style": {"duck", "grilled_dark_meat", "other"}, "game_type": {"delicate_feathered_game", "other"}, "cheese_type": {"blue", "fresh", "hard", "other"}, "dessert_base": {"cocoa", "chocolate", "dark_berries", "fruit", "cream", "other"}, "is_dessert": {True, False}, "fatty_cream_sauce": {True, False}}


class PipelineError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def validate_filters(value: dict | None) -> dict:
    if value is None:
        return {}
    if type(value) is not dict or set(value) - FILTERS:
        raise PipelineError("invalid_filters", "Unsupported or invalid filter fields")
    result = {}
    for key, item in value.items():
        if key in LIST_FILTERS:
            if type(item) is not list or len(item) > 2500 or any(type(x) is not str or not x.strip() or len(x) > 400 for x in item):
                raise PipelineError("invalid_filters", "Invalid list filter: " + key)
            result[key] = list(dict.fromkeys(item))
        elif key in {"color", "sweetness", "wine_kind"}:
            choices = {"color": COLORS, "sweetness": SWEETNESS, "wine_kind": KINDS}[key]
            if type(item) is not str or item not in choices:
                raise PipelineError("invalid_filters", "Invalid categorical filter: " + key)
            result[key] = item
        elif key == "exclude_producer":
            if type(item) is not str or not item.strip() or len(item) > 400:
                raise PipelineError("invalid_filters", "Invalid producer exclusion")
            result[key] = item
        elif key == "in_stock":
            if type(item) is not bool:
                raise PipelineError("invalid_filters", "in_stock must be boolean")
            result[key] = item
        else:
            if not known_number(item) or item < 0:
                raise PipelineError("invalid_filters", "Invalid numeric limit: " + key)
            result[key] = item
    if len(canonical(result).encode()) > MAX_FILTER_BYTES:
        raise PipelineError("invalid_filters", "Combined filters exceed 128 KiB")
    return result


def validate_attributes(value: dict | None) -> dict:
    if value is None:
        return {}
    if type(value) is not dict or set(value) - set(ATTRIBUTES):
        raise PipelineError("invalid_attributes", "Unsupported confirmed attribute")
    for key, item in value.items():
        if key in {"is_dessert", "fatty_cream_sauce"}:
            valid = type(item) is bool
        else:
            valid = type(item) is str and item in ATTRIBUTES[key]
        if not valid:
            raise PipelineError("invalid_attributes", "Invalid confirmed attribute: " + key)
    return dict(value)


@dataclass(frozen=True)
class PreparedFilters:
    excluded_producers: frozenset
    blocked_slugs: frozenset
    restaurant_slugs: frozenset | None
    included_grapes: frozenset
    excluded_grapes: frozenset


def prepare_filters(filters: dict) -> PreparedFilters:
    exclusions = [*filters.get("exclude_producers", [])]
    if "exclude_producer" in filters:
        exclusions.append(filters["exclude_producer"])
    return PreparedFilters(
        frozenset(normalize(x) for x in exclusions),
        frozenset(filters.get("seen_wine_slugs", [])) | frozenset(filters.get("rejected_wine_slugs", [])),
        frozenset(filters["restaurant_wine_slugs"]) if "restaurant_wine_slugs" in filters else None,
        frozenset(normalize(g) for g in filters.get("grapes_include", [])),
        frozenset(normalize(g) for g in filters.get("grapes_exclude", [])),
    )


def rejection_reasons(wine: dict, eligibility: dict, filters: dict, *, prepared: PreparedFilters | None = None) -> list[str]:
    """The only admission gate; semantic ranking and generated prose cannot change it."""
    reasons = []
    prepared = prepared if prepared is not None else prepare_filters(filters)
    if wine.get("catalog_state") != "Active":
        reasons.append("catalog_not_active")
    if wine.get("discovery_eligible") is not True:
        reasons.append("discovery_ineligible")
    for field, plural in [("color", "colors"), ("sweetness", "sweetness"), ("wine_kind", "wine_kinds")]:
        if wine.get(field) not in eligibility[plural]:
            reasons.append("profile_" + field)
        if field in filters and wine.get(field) != filters[field]:
            reasons.append("requested_" + field)
    limits = [("alcohol_percent", eligibility.get("max_alcohol_percent"), "profile_alcohol"),
              ("alcohol_percent", filters.get("max_alcohol_percent"), "requested_alcohol"),
              ("price", filters.get("max_price_rub"), "price"),
              ("residual_sugar_g_l", filters.get("max_sugar_g_l"), "residual_sugar")]
    for field, limit, reason in limits:
        if limit is not None:
            actual = wine.get(field)
            if not known_number(actual) or actual > limit:
                reasons.append(reason)
    if prepared.excluded_producers and (not wine.get("producer") or normalize(wine["producer"]) in prepared.excluded_producers):
        reasons.append("excluded_or_unknown_producer")
    slug = wine["slug"]
    if slug in prepared.blocked_slugs:
        reasons.append("already_seen_or_rejected")
    if prepared.restaurant_slugs is not None and slug not in prepared.restaurant_slugs:
        reasons.append("not_on_restaurant_list")
    if filters.get("in_stock") and wine.get("stock") is not True:
        reasons.append("stock_unconfirmed")
    grapes = {normalize(g) for g in wine.get("reported_grapes", [])}
    if not prepared.included_grapes.issubset(grapes):
        reasons.append("required_grape_unconfirmed")
    excluded_grapes = prepared.excluded_grapes
    if excluded_grapes and (wine.get("grape_list_completeness") != "verified_complete" or bool(grapes & excluded_grapes)):
        reasons.append("excluded_grape_or_incomplete_blend")
    return reasons


class Engine:
    def __init__(self, knowledge: Knowledge, index: EmbeddingIndex, *, cursor_secret: bytes | None = None, cursor_ttl_seconds: int = 3600, clock=time.time):
        self.knowledge = knowledge
        self.index = index
        self.secret = cursor_secret if cursor_secret is not None else secrets.token_bytes(32)
        if type(self.secret) is not bytes or len(self.secret) < 32:
            raise ValueError("Cursor secret must contain at least 32 bytes")
        if type(cursor_ttl_seconds) is not int or not 1 <= cursor_ttl_seconds <= 86400:
            raise ValueError("Cursor lifetime must contain 1 to 86400 seconds")
        self.cursor_ttl_seconds = cursor_ttl_seconds
        self.clock = clock
        self.version = digest({"dataset": knowledge.sha256, "index": index.version, "ranking": RANKING_VERSION})

    def _encode_cursor(self, state: dict) -> str:
        body = canonical(state).encode()
        signature = hmac.new(self.secret, body, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(body).decode().rstrip("=") + "." + base64.urlsafe_b64encode(signature).decode().rstrip("=")

    def _decode_cursor(self, token: str) -> dict:
        try:
            if type(token) is not str or len(token) > 1_500_000:
                raise ValueError()
            body, signature = token.split(".")
            if not re.fullmatch(r"[A-Za-z0-9_-]+", body) or not re.fullmatch(r"[A-Za-z0-9_-]+", signature):
                raise ValueError()
            body_raw = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
            signature_raw = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
            if not hmac.compare_digest(signature_raw, hmac.new(self.secret, body_raw, hashlib.sha256).digest()):
                raise ValueError()
            state = json.loads(body_raw)
            if type(state) is not dict or state.get("version") != self.version:
                raise PipelineError("stale_cursor", "The catalog, index or ranking version changed")
            if type(state.get("expires")) is not int or state["expires"] <= self.clock():
                raise PipelineError("expired_cursor", "The continuation cursor expired")
            return state
        except PipelineError:
            raise
        except (ValueError, TypeError, KeyError, UnicodeError):
            raise PipelineError("invalid_cursor", "The continuation cursor is invalid") from None

    def _context(self, node_id: str, filters: dict, attributes: dict, scope: list[str] | None, resolution: dict | None, limit: int) -> dict:
        if type(node_id) is not str or node_id not in self.knowledge.nodes:
            raise PipelineError("unknown_node", "Select an exact known dish or category")
        if type(limit) is not int or not 1 <= limit <= 10:
            raise PipelineError("invalid_limit", "Page size must be an integer from 1 to 10")
        filters = validate_filters(filters)
        attrs = validate_attributes(attributes)
        if scope is not None and (type(scope) is not list or len(scope) > 3000 or any(type(s) is not str or s not in self.knowledge.wines for s in scope)):
            raise PipelineError("invalid_scope", "Scope must contain exact catalog wine ids")
        context = {"node_id": node_id, "filters": filters, "attributes": attrs,
                "catalog_scope": sorted(set(scope)) if scope is not None else None,
                "resolution": resolution or {}, "limit": limit}
        if len(canonical(context).encode()) > MAX_CONTEXT_BYTES:
            raise PipelineError("invalid_context", "Selection context exceeds 512 KiB")
        return context

    def recommend(self, *, confirmed_dish: str | None = None, node_id: str | None = None,
                  filters: dict | None = None, confirmed_attributes: dict | None = None,
                  catalog_scope: list[str] | None = None, limit: int = 3,
                  resolution: dict | None = None) -> dict:
        if confirmed_dish is not None:
            if type(confirmed_dish) is not str or not confirmed_dish.strip() or len(confirmed_dish) > 500:
                raise PipelineError("invalid_dish", "A nonempty dish label is required")
            resolved = self.knowledge.resolve(confirmed_dish)
            if node_id is not None and node_id != resolved:
                raise PipelineError("conflicting_resolution", "Dish name and node id do not agree")
            node_id = resolved
        if node_id is None:
            validate_filters(filters)
            validate_attributes(confirmed_attributes)
            return {"status": "needs_category", "resolved_node_id": None, "results": [],
                    "wine_slugs": [], "explanations": [], "next_cursor": None,
                    "needs_clarification": True, "clarification_question": "Какое блюдо или категорию еды выбрать?",
                    "categories": [{"id": n["id"], "label": n["label_ru"]} for n in self.knowledge.nodes.values() if n["kind"] == "fallback_class"]}
        node = self.knowledge.nodes.get(node_id) if type(node_id) is str else None
        ambiguity = self.knowledge.disambiguations.get(normalize(confirmed_dish)) if confirmed_dish is not None else None
        if node and ((ambiguity and ambiguity.get("introduced_in") == "2.0.0")
                     or (node.get("introduced_in") == "2.0.0" and node["kind"] == "class")):
            resolution = dict(resolution or {})
            resolution["needs_clarification"] = True
            resolution["clarification_question"] = (resolution.get("clarification_question") or node.get("clarifying_question_ru")
                or "Какие основные ингредиенты и соус, насколько блюдо сладкое и острое?")
        context = self._context(node_id, filters if filters is not None else {}, confirmed_attributes if confirmed_attributes is not None else {}, catalog_scope, resolution, limit)
        return self._page(context, 0)

    def more(self, cursor: str, *, filters: dict | None = None, confirmed_attributes: dict | None = None) -> dict:
        state = self._decode_cursor(cursor)
        context = state["context"]
        if filters is not None and digest(validate_filters(filters)) != digest(context["filters"]):
            raise PipelineError("cursor_context_changed", "Filters changed; start a new selection")
        if confirmed_attributes is not None and digest(validate_attributes(confirmed_attributes)) != digest(context["attributes"]):
            raise PipelineError("cursor_context_changed", "Recipe attributes changed; start a new selection")
        return self._page(context, state["offset"], expected_ranking=state["ranking_sha256"], expires=state["expires"])

    def _page(self, context: dict, offset: int, *, expected_ranking: str | None = None, expires: int | None = None) -> dict:
        node_id = context["node_id"]
        node = self.knowledge.nodes[node_id]
        profile_id, boosts, modifiers, eligibility = self.knowledge.effective_profile(node_id, context["attributes"])
        rule_attributes = self.knowledge.rule_context(node_id, context["attributes"])["effective_rule_attributes"]
        profile = self.knowledge.profiles[profile_id]
        filters = context["filters"]
        prepared = prepare_filters(filters)
        scope = set(context["catalog_scope"]) if context["catalog_scope"] is not None else None
        blocked_curated = set()
        if profile_id == node["pairing_rule"]["profile_id"]:
            blocked_curated = {entry["wine_slug"] for entry in node["curated"]
                               if not all(predicate(rule, rule_attributes)
                                          for rule in entry.get("applicability_conditions", []))}
        eligible, rejected = {}, Counter()
        for slug, wine in self.knowledge.wines.items():
            if scope is not None and slug not in scope:
                continue
            reasons = rejection_reasons(wine, eligibility, filters, prepared=prepared)
            style_rejection = self.knowledge.style_rejection(slug, node_id, profile_id, context["attributes"])
            if style_rejection:
                reasons.append(style_rejection)
            if slug in blocked_curated:
                reasons.append("curated_applicability_unconfirmed")
            if reasons:
                rejected.update(reasons)
            else:
                eligible[slug] = wine
        query_key, query_text = self.knowledge.query(profile_id, boosts)
        scores = self.index.similarities(query_key, list(eligible)) if eligible else {}
        applicable = []
        # A changed effective style uses its own curated pool; never relabel old picks silently.
        if profile_id == node["pairing_rule"]["profile_id"]:
            entries = sorted(node["curated"], key=lambda e: e["rank"])
            for entry in entries:
                if entry["wine_slug"] in eligible and all(predicate(p, rule_attributes) for p in entry.get("applicability_conditions", [])):
                    applicable.append(entry)
        else:
            for rank, slug in enumerate(profile["curation_pool"], 1):
                if slug in eligible:
                    applicable.append({"wine_slug": slug, "rank": rank, "explanation_ru": profile["match_rationale_ru"]})
        curated = {e["wine_slug"]: e for e in applicable}
        preferred = {normalize(g) for g in profile["target"].get("preferred_grapes", [])}

        def structured_fit(slug):
            return len(preferred & {normalize(g) for g in eligible[slug].get("reported_grapes", [])})

        def evidence_count(slug):
            return sum(eligible[slug].get(k) is not None for k in ["color", "sweetness", "wine_kind", "producer", "alcohol_percent"])

        retrieved = sorted((s for s in eligible if s not in curated),
                           key=lambda s: (-evidence_count(s), -structured_fit(s), -scores[s], s))
        curated_order = [e["wine_slug"] for e in applicable]
        first_page, used_producers = [], set()
        for slug in curated_order:
            producer = normalize(eligible[slug].get("producer") or "<unknown>")
            if producer not in used_producers and len(first_page) < context["limit"]:
                first_page.append(slug)
                used_producers.add(producer)
        remaining_curated = [s for s in curated_order if s not in first_page]
        # Finish the editorial stage before discovery. A short first page is preferable
        # to hiding remaining editorial choices or repeating a producer on that page.
        if not remaining_curated:
            for slug in retrieved:
                producer = normalize(eligible[slug].get("producer") or "<unknown>")
                if producer not in used_producers and len(first_page) < context["limit"]:
                    first_page.append(slug)
                    used_producers.add(producer)
        order = first_page + remaining_curated + [s for s in retrieved if s not in first_page]
        ranking_hash = digest({"profile": profile_id, "boosts": boosts, "order": order})
        if expected_ranking is not None and ranking_hash != expected_ranking:
            raise PipelineError("stale_cursor", "Eligible ranking changed; start a new selection")
        if type(offset) is not int or not 0 <= offset <= len(order):
            raise PipelineError("invalid_cursor", "Invalid continuation offset")
        page_limit = len(first_page) if offset == 0 else context["limit"]
        selected = order[offset:offset + page_limit]
        rows = []
        for slug in selected:
            wine = eligible[slug]
            # Final admission check guards every output path, including editorial entries.
            if (rejection_reasons(wine, eligibility, filters, prepared=prepared)
                    or self.knowledge.style_rejection(slug, node_id, profile_id, context["attributes"])):
                raise RuntimeError("Eligibility invariant violated")
            reason = curated[slug]["explanation_ru"] if slug in curated else "Соответствует выбранному стилю вина для блюда. " + wine["description"]
            if self.knowledge.suitability_policy:
                if slug not in curated:
                    rationale = profile["match_rationale_ru"]
                    reason = f"К «{node['label_ru']}»: {rationale[:1].upper() + rationale[1:]}. {wine['description']}"
                elif profile_id != node["pairing_rule"]["profile_id"]:
                    reason = f"К «{node['label_ru']}»: {reason[:1].upper() + reason[1:]}. {wine['description']}"
                pairing_attrs = self.knowledge.rule_context(node_id, context["attributes"])["effective_rule_attributes"]
                details = []
                if pairing_attrs.get("heat") in {"medium", "high"}:
                    alcohol = f"{wine['alcohol_percent']:g}".replace(".", ",")
                    reason += f" С учётом остроты блюда выбрано вино умеренной крепости — {alcohol}%."
                if (pairing_attrs.get("sauce_sweetness") in {"medium", "high"}
                        and profile_id in {"sweet_glaze", "sweet_glaze_rich_meat", "sweet_glaze_duck", "spicy", "spicy_sour"}):
                    details.append("сладость соуса")
                if pairing_attrs.get("acidity") == "high":
                    details.append("кислая подача")
                if (pairing_attrs.get("fatty_cream_sauce") is True
                        and (profile_id == "white_butter_cream" or pairing_attrs.get("poultry_style") == "duck")):
                    details.append("сливочная жирность")
                if details:
                    reason += " Учитываются: " + ", ".join(details) + "."
            rows.append({"wine_slug": slug, "name": wine["name"], "producer": wine.get("producer"),
                         "source_url": wine.get("source_url"), "selection_source": "curated" if slug in curated else "embedding",
                         "reason": reason, "facts": {k: wine.get(k) for k in ["color", "sweetness", "wine_kind", "alcohol_percent", "price", "stock", "residual_sugar_g_l", "reported_grapes"]},
                         "ranking_evidence": {"semantic_similarity": scores[slug], "preferred_grape_matches": structured_fit(slug), "known_fact_count": evidence_count(slug)},
                         "fact_evidence": wine.get("evidence", {})})
        end = offset + len(selected)
        expiry = expires if expires is not None else int(self.clock()) + self.cursor_ttl_seconds
        cursor = self._encode_cursor({"version": self.version, "expires": expiry, "context": context,
                                      "offset": end, "ranking_sha256": ranking_hash}) if end < len(order) else None
        resolution = context["resolution"]
        no_options = not eligible
        question = resolution.get("clarification_question")
        if no_options:
            question = "Нет вин с подтверждёнными данными, удовлетворяющих ограничениям. Уточнить ограничения или данные каталога?"
        return {"status": "no_results" if no_options else "ok", "resolved_node_id": node_id,
                "specificity": node["kind"], "effective_profile_id": profile_id,
                "confirmed_attributes": context["attributes"], "applied_modifier_ids": modifiers,
                "wine_slugs": selected, "results": rows,
                "explanations": [{"wine_slug": row["wine_slug"], "reason": row["reason"]} for row in rows],
                "needs_clarification": no_options or resolution.get("needs_clarification", False),
                "clarification_question": question, "resolution": resolution,
                "next_cursor": cursor, "shown_count": end, "total_eligible": len(eligible),
                "seen_wine_slugs": list(dict.fromkeys(filters.get("seen_wine_slugs", []) + order[:end])),
                "diagnostics": {"rejected_reason_counts": dict(rejected), "curated_eligible": len(curated),
                                "query_text": query_text, "embedding_model": self.index.model,
                                "ranking_version": RANKING_VERSION, "bundle_version": self.version,
                                "sauce_rule_context": self.knowledge.rule_context(node_id, context["attributes"]),
                                "style_policy_version": self.knowledge.suitability_policy["version"] if self.knowledge.suitability_policy else None}}

    def recommend_from_recognition(self, recognition: dict, **options) -> dict:
        if type(recognition) is not dict:
            raise PipelineError("invalid_recognition", "Recognition must be an object")
        node_id = recognition.get("visual_node_id")
        hypothesis = recognition.get("hypothesis_node_id")
        for value in [node_id, hypothesis]:
            if value is not None and (type(value) is not str or value not in self.knowledge.nodes):
                raise PipelineError("invalid_recognition", "Recognition returned an unknown taxonomy id")
        resolution = {"source": "photograph", "visual_node_id": node_id, "hypothesis_node_id": hypothesis,
                      "needs_clarification": recognition.get("needs_clarification") is True,
                      "clarification_question": recognition.get("clarification_question"),
                      "recipe_confirmed_by_user": False, "guardrail_demoted": False}
        if node_id is not None and self.knowledge.nodes[node_id]["kind"] == "dish":
            # Exact recipes need confirmation. A VLM hypothesis is never a user confirmation.
            original = self.knowledge.nodes[node_id]
            node_id = original["parent_id"]
            resolution.update(guardrail_demoted=True, needs_clarification=True,
                              clarification_question=original["clarifying_question_ru"])
        return self.recommend(node_id=node_id, resolution=resolution, **options)
