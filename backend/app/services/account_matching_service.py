from dataclasses import dataclass, field
from typing import Any

from rapidfuzz import fuzz, process

from app.domain.entities import Account, AccountAlias
from app.domain.enums import MatchType, RowStatus


@dataclass(slots=True)
class AccountCatalog:
    accounts: list[Account] = field(default_factory=list)
    aliases: list[AccountAlias] = field(default_factory=list)


@dataclass(slots=True)
class MatchResult:
    account: Account | None
    match_type: MatchType
    status: RowStatus
    confidence: float
    reason: str | None = None


def match_account(candidate: dict[str, Any], catalog: AccountCatalog) -> MatchResult:
    code = _as_string(candidate.get("code"))
    normalized_name = _as_string(candidate.get("normalized_name")) or ""

    if code:
        exact_accounts = [account for account in catalog.accounts if account.code == code]
        if len(exact_accounts) == 1:
            return MatchResult(exact_accounts[0], MatchType.EXACT_CODE, RowStatus.MATCHED, 1.0)

        code_and_name = [
            account
            for account in exact_accounts
            if account.normalized_name == normalized_name
        ]
        if len(code_and_name) == 1:
            return MatchResult(code_and_name[0], MatchType.CODE_AND_NAME, RowStatus.MATCHED, 1.0)

    name_matches = [
        account for account in catalog.accounts if account.normalized_name == normalized_name
    ]
    if len(name_matches) == 1:
        return MatchResult(name_matches[0], MatchType.NORMALIZED_NAME, RowStatus.MATCHED, 1.0)
    if len(name_matches) > 1:
        context_codes = {
            _as_string(context_code)
            for context_code in candidate.get("context_codes", [])
        }
        contextual_matches = [
            account for account in name_matches if account.parent_code in context_codes
        ]
        if len(contextual_matches) == 1:
            return MatchResult(contextual_matches[0], MatchType.CONTEXT, RowStatus.MATCHED, 1.0)
        return MatchResult(None, MatchType.NONE, RowStatus.NEEDS_REVIEW, 0, "AMBIGUOUS")

    alias_matches = _accounts_for_alias(normalized_name, catalog)
    if len(alias_matches) == 1:
        return MatchResult(alias_matches[0], MatchType.ALIAS, RowStatus.MATCHED, 1.0)
    if len(alias_matches) > 1:
        return MatchResult(None, MatchType.NONE, RowStatus.NEEDS_REVIEW, 0, "AMBIGUOUS")

    if not normalized_name:
        return MatchResult(None, MatchType.NONE, RowStatus.UNKNOWN, 0, "NO_ACCOUNT_NAME")

    choices = {account.code: account.normalized_name for account in catalog.accounts}
    fuzzy_match = process.extractOne(normalized_name, choices, scorer=fuzz.ratio, score_cutoff=70)
    if fuzzy_match:
        _, score, account_code = fuzzy_match
        account = next(account for account in catalog.accounts if account.code == account_code)
        return MatchResult(
            account,
            MatchType.FUZZY,
            RowStatus.NEEDS_REVIEW,
            round(score / 100, 2),
            "FUZZY_SUGGESTION",
        )

    return MatchResult(None, MatchType.NONE, RowStatus.UNKNOWN, 0, "NO_MATCH")


def _accounts_for_alias(normalized_name: str, catalog: AccountCatalog) -> list[Account]:
    codes = {
        alias.account_code
        for alias in catalog.aliases
        if alias.normalized_alias == normalized_name
    }
    return [account for account in catalog.accounts if account.code in codes]


def _as_string(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
