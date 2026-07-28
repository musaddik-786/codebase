"""
guidewire_client.py
───────────────────
All HTTP calls to the Guidewire PolicyCenter and ClaimCenter REST APIs.

PolicyCenter base : https://pc-sandbox-gwcpdev.hexaware.zeta1-andromeda.guidewire.net/rest
ClaimCenter base  : https://cc-sandbox-gwcpdev.hexaware.zeta1-andromeda.guidewire.net/rest
"""

import logging
import os
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

PC_BASE_URL = os.environ.get(
    "GW_PC_BASE_URL",
    "https://pc-sandbox-gwcpdev.hexaware.zeta1-andromeda.guidewire.net/rest",
)
CC_BASE_URL = os.environ.get(
    "GW_CC_BASE_URL",
    "https://cc-sandbox-gwcpdev.hexaware.zeta1-andromeda.guidewire.net/rest",
)
GW_AUTH = os.environ.get("GW_AUTHORIZATION", "Basic c3U6Z3c=")

HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/json",
    "authorization": GW_AUTH,
}

REQUEST_TIMEOUT = int(os.environ.get("GW_TIMEOUT_SECONDS", "30"))


# ── Low-level helpers ─────────────────────────────────────────────────────────

def _pc_post(uri: str, body: dict) -> dict:
    url = PC_BASE_URL + uri
    log.info("GW PC POST %s", url)
    resp = requests.post(url, json=body, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    _raise_for_status(resp, "PC POST", uri)
    return resp.json()


def _pc_get(uri: str, params: Optional[dict] = None) -> dict:
    url = PC_BASE_URL + uri
    log.info("GW PC GET %s", url)
    resp = requests.get(url, headers=HEADERS, params=params, timeout=REQUEST_TIMEOUT)
    _raise_for_status(resp, "PC GET", uri)
    return resp.json()


def _cc_post(uri: str, body: dict) -> dict:
    url = CC_BASE_URL + uri
    log.info("GW CC POST %s", url)
    resp = requests.post(url, json=body, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    _raise_for_status(resp, "CC POST", uri)
    return resp.json()


def _raise_for_status(resp: requests.Response, method: str, uri: str):
    if not resp.ok:
        log.error(
            "Guidewire %s %s → HTTP %s: %s",
            method, uri, resp.status_code, resp.text[:500],
        )
        resp.raise_for_status()


# ── PolicyCenter — Policy Search ──────────────────────────────────────────────

def search_policy(policy_number: str) -> dict:
    """
    Search for a policy in Guidewire PolicyCenter by policy number.
    Uses: POST /policy/v1/search/policies
    """
    body = {
        "data": {
            "attributes": {
                "policyNumber": policy_number
            }
        }
    }
    return _pc_post("/policy/v1/search/policies", body)


def get_policy_coverages(policy_id: str) -> dict:
    """
    Retrieve detailed coverage information for a policy from Guidewire.
    Uses: GET /policy/v1/policies/{policyId}
    """
    result = _pc_get(f"/policy/v1/policies/{policy_id}")
    if isinstance(result, dict):
        data = result.get("data", {})
        if isinstance(data, list):
            log.info("[GW RAW] /policies/%s → data is LIST(%d); first item keys: %s", policy_id, len(data), sorted(data[0].keys()) if data and isinstance(data[0], dict) else "empty")
            inner_attrs = (data[0].get("attributes", {}) if data and isinstance(data[0], dict) else {})
        elif isinstance(data, dict):
            log.info("[GW RAW] /policies/%s → data is DICT; keys: %s", policy_id, sorted(data.keys()))
            inner_attrs = data.get("attributes", {})
        else:
            inner_attrs = {}
        log.info("[GW RAW] attributes keys: %s", sorted(inner_attrs.keys()) if isinstance(inner_attrs, dict) else type(inner_attrs).__name__)
        log.info("[GW RAW] totalPremium=%s", inner_attrs.get("totalPremium") if isinstance(inner_attrs, dict) else "N/A")
    return result


# ── ClaimCenter — Loss / FNOL Reporting ──────────────────────────────────────

def report_loss_to_guidewire(
    policy_number: str,
    claim_number: str,
    loss_type: str,
    loss_date: str,
    loss_description: str,
    policyholder_name: str,
    loss_location: Optional[str] = None,
    estimated_amount: Optional[float] = None,
) -> dict:
    """
    Reports a new loss (FNOL) to Guidewire ClaimCenter.
    Uses: POST /claim/v1/fnols
    """
    loss_cause_map = {
        "water damage": "WaterDamage",
        "fire":         "Fire",
        "fire damage":  "Fire",
        "wind/hail":    "WindHail",
        "hail":         "WindHail",
        "wind":         "WindHail",
        "tree damage":  "WindHail",
        "theft":        "Theft",
        "structural":   "Other",
        "motor":        "Collision",
        "auto":         "Collision",
        "collision":    "Collision",
    }
    loss_cause = loss_cause_map.get(loss_type.lower().strip(), "Other")

    body = {
        "data": {
            "attributes": {
                "policyNumber": policy_number,
                "lossDate": loss_date,
                "lossCause": loss_cause,
                "description": loss_description,
                "claimNumber": claim_number,
                "insured": {"displayName": policyholder_name},
            }
        }
    }
    if loss_location:
        body["data"]["attributes"]["lossLocation"] = {"displayName": loss_location}
    if estimated_amount is not None:
        body["data"]["attributes"]["estimatedTotalClaim"] = {
            "amount": estimated_amount,
            "currency": "USD",
        }

    return _cc_post("/claim/v1/fnols", body)


# ── Response parsers ──────────────────────────────────────────────────────────

def parse_policy_from_search(gw_response: dict) -> Optional[dict]:
    """
    Extract a flat normalised policy dict from a Guidewire search response.
    Returns None if no policies were found.
    """
    try:
        data_list = gw_response.get("data", [])
        if not data_list:
            log.warning("No policy data returned from Guidewire")
            return None

        policy = data_list[0]
        attrs = policy.get("attributes", {})

        parsed = {
            "gw_policy_id":    attrs.get("policyId", ""),
            "policy_number":   attrs.get("policyNumber", ""),
            "status":          attrs.get("status", "Unknown"),
            "effective_date":  attrs.get("effectiveDate", ""),
            "expiration_date": attrs.get("expirationDate", ""),
            "coverage_types":  attrs.get("coverageTypes", []),
            "policyholder_name":    attrs.get("insuredName", ""),
            "policyholder_address": attrs.get("policyAddress", ""),
            "account_number":  attrs.get("accountNumber", ""),
            "product_name":    (attrs.get("product") or {}).get("displayName", ""),
            "raw":             gw_response,
        }

        log.info("Parsed policy: %s", {k: v for k, v in parsed.items() if k != "raw"})
        return parsed

    except Exception as exc:
        log.exception("Failed to parse Guidewire policy response")
        raise ValueError(f"Unable to parse Guidewire response: {str(exc)}")
