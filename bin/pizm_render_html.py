#!/usr/bin/env python3
"""Deterministic HTML presenter for a frozen Pizm run directory.

Human-reading presentation of frozen Pizm artifacts.
No provider/network calls, no wall clock, no extra JSON interpreter:
loaders are imported from `bin/pizm-session-bundle`.
"""
from __future__ import annotations

import html
import importlib.util
import json
import re
import sys
from pathlib import Path

_BUNDLE = None

_TOKEN_KEYS = (
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
)
_COST_KEY = "estimated_cost"
_ALLOWED_DISPLAY = (
    "semantic_stage_count",
    "host_inference_count",
    "model_repair_count",
    "checkpoint_retry_count",
    "candidate_bytes",
    "development_bytes",
)
_KNOWN_CAND_KEYS = {"candidate_id", "title", "semantic_core", "epistemics"}
_CORE_FIELDS = (
    ("Core claim", "claim"),
    ("Structural shift", "structural_shift"),
    ("Mechanism", "mechanism"),
    ("Grounding anchor", "grounding_anchor"),
    ("Becomes visible", "what_becomes_visible"),
    ("Boundary", "boundary"),
)
_BUNDLE_FIELDS = (
    ("Bundle thesis", "bundle_thesis"),
    ("Composition gain", "composition_gain"),
    ("New consequence / prediction", "new_consequence_or_prediction"),
    ("Internal tension", "internal_tension"),
    ("Weakest link", "weakest_link"),
)
_LOCK_FIELDS = (
    ("Core claim", "core_claim"),
    ("Structural shift", "structural_shift"),
    ("Boundary", "boundary"),
)
_LEVER_FIELDS = (
    ("Intervention / test point", "intervention_or_test_point"),
    ("Model link", "model_link"),
    ("Minimum bounded move", "minimum_bounded_move"),
    ("Expected observation / response", "expected_observation_or_response"),
    ("Disconfirming signal", "disconfirming_signal"),
    ("Stop condition", "stop_condition"),
    ("Remaining assumptions", "remaining_assumptions"),
    ("Adaptation / countermove", "adaptation_or_countermove"),
)
_KNOWN_STAGE_PREFIXES = (
    "candidates",
    "search-field",
    "search-pass",
    "portfolio",
    "development-v2",
    "deep-review-v2",
    "comparison-review",
)
_KNOWN_STAGE_NAMES = {
    "design.json",
    "review.json",
    "manifest.json",
    "selection.json",
}


def _bundle():
    global _BUNDLE
    if _BUNDLE is not None:
        return _BUNDLE
    main = sys.modules.get("__main__")
    if main is not None and hasattr(main, "_load_frozen_json"):
        _BUNDLE = main
        return _BUNDLE
    name = "pizm_session_bundle_cli"
    if name in sys.modules and hasattr(sys.modules[name], "_load_frozen_json"):
        _BUNDLE = sys.modules[name]
        return _BUNDLE
    path = Path(__file__).resolve().parent / "pizm-session-bundle"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import loaders from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    _BUNDLE = mod
    return _BUNDLE


def _e(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _prose(value) -> str:
    text = "" if value is None else str(value)
    return "<br>\n".join(_e(line) for line in text.split("\n"))


def _aid(prefix: str, raw: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", raw).strip("-")
    if not slug:
        slug = "x"
    return f"{prefix}-{slug}"


def _try_candidate(cli, ref, cand_index):
    try:
        return cli._candidate_by_ref(ref, cand_index)
    except ValueError:
        return None


def _resolve_task(run_dir: Path, task) -> str:
    if task is not None and str(task).strip():
        return str(task).strip()
    path = run_dir / "run.md"
    if not path.is_file():
        return "Not specified"
    text = path.read_text(encoding="utf-8")
    capturing = False
    buf = []
    for line in text.splitlines():
        if re.match(r"^#+\s+Task\s*$", line):
            capturing = True
            continue
        if capturing:
            if re.match(r"^#+\s+\S", line):
                break
            buf.append(line)
    body = "\n".join(buf).strip()
    return body if body else "Not specified"


def _optional_json(cli, run_dir: Path, name: str):
    if not (run_dir / name).is_file():
        return None
    cli._verify_frozen_sidecar(run_dir, name)
    return cli._load_frozen_json(run_dir, name)


def _load_meta(cli, run_dir: Path, json_name: str):
    meta_name = json_name[: -len(".json")] + ".meta.json"
    path = run_dir / meta_name
    if not path.is_file():
        return None
    try:
        return cli._load_frozen_json(run_dir, meta_name)
    except ValueError:
        return None


def _sha_text(run_dir: Path, json_name: str):
    sha_name = json_name[: -len(".json")] + ".sha256"
    path = run_dir / sha_name
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8").strip() or None


def _load_candidate_passes(cli, run_dir: Path):
    passes = []
    for name in ("candidates.json", "candidates-pass01.json"):
        if (run_dir / name).is_file():
            cli._verify_frozen_sidecar(run_dir, name)
            passes.append(("pass01", name, cli._load_frozen_json(run_dir, name)))
            break
    for n in range(2, 10):
        pid = f"pass{n:02d}"
        found = None
        for name in (f"candidates-pass{n:02d}.json", f"search-pass{n:02d}.json"):
            if (run_dir / name).is_file():
                found = name
                break
        if found is None:
            continue
        cli._verify_frozen_sidecar(run_dir, found)
        passes.append((pid, found, cli._load_frozen_json(run_dir, found)))
    return passes


def _glob_stage(run_dir: Path, prefix: str):
    names = []
    for p in run_dir.iterdir():
        if not p.is_file():
            continue
        n = p.name
        if n.endswith(".meta.json"):
            continue
        if n.startswith(prefix) and n.endswith(".json"):
            names.append(n)
    names.sort()
    return names


def _is_known_stage_name(name: str) -> bool:
    if name.endswith(".meta.json"):
        return True
    if name in _KNOWN_STAGE_NAMES:
        return True
    return any(name.startswith(p) for p in _KNOWN_STAGE_PREFIXES)


def _load_run(run_dir: Path) -> dict:
    cli = _bundle()
    passes = _load_candidate_passes(cli, run_dir)
    cand_index = {}
    for pid, _name, data in passes:
        part = cli._candidate_index(data, pid)
        for key, cand in part.items():
            if key in cand_index:
                raise ValueError(f"duplicate composite candidate key: {key!r}")
            cand_index[key] = cand

    search_field = _optional_json(cli, run_dir, cli._SEARCH_FIELD_NAME)
    if search_field is not None:
        seen = set()
        for entry in search_field.get("entries") or []:
            if entry in seen:
                raise ValueError(f"duplicate search field entry: {entry!r}")
            seen.add(entry)

    portfolio = _optional_json(cli, run_dir, "portfolio.json")
    p_map = {}
    if portfolio is not None:
        p_map = cli._derive_promoted_p_ids(portfolio)

    dev_names = _glob_stage(run_dir, "development-v2")
    all_devs = []
    for name in dev_names:
        cli._verify_frozen_sidecar(run_dir, name)
        all_devs.append((name, cli._load_frozen_json(run_dir, name)))

    dev_by_target = {}
    loaded_dev_names = []
    for name, data in all_devs:
        loaded_dev_names.append(name)
        target = data.get("target") if isinstance(data.get("target"), dict) else {}
        tid = target.get("target_id") or data.get("target_id") or "default"
        is_suffixed = bool(re.match(r"^development-v2-[PB0-9A-Za-z_]+\.json$", name))
        if tid not in dev_by_target:
            dev_by_target[tid] = (name, data, is_suffixed)
        else:
            prev_name, prev_data, prev_suffixed = dev_by_target[tid]
            if is_suffixed and not prev_suffixed:
                dev_by_target[tid] = (name, data, is_suffixed)
    developments = [(name, data) for name, data, _ in dev_by_target.values()]

    review_names = _glob_stage(run_dir, "deep-review-v2")
    all_revs = []
    for name in review_names:
        cli._verify_frozen_sidecar(run_dir, name)
        all_revs.append((name, cli._load_frozen_json(run_dir, name)))

    rev_by_target = {}
    loaded_rev_names = []
    for name, data in all_revs:
        loaded_rev_names.append(name)
        tid = data.get("target_id") or (
            data.get("target", {}).get("target_id")
            if isinstance(data.get("target"), dict)
            else "default"
        )
        is_suffixed = bool(re.match(r"^deep-review-v2-[PB0-9A-Za-z_]+\.json$", name))
        if tid not in rev_by_target:
            rev_by_target[tid] = (name, data, is_suffixed)
        else:
            prev_name, prev_data, prev_suffixed = rev_by_target[tid]
            if is_suffixed and not prev_suffixed:
                rev_by_target[tid] = (name, data, is_suffixed)
    reviews = [(name, data) for name, data, _ in rev_by_target.values()]
    comparison = None
    for name in ("comparison-review-v1.json", "comparison-review.json"):
        loaded = _optional_json(cli, run_dir, name)
        if loaded is not None:
            comparison = (name, loaded)
            break

    has_design = (run_dir / cli._LEVER_DESIGN_NAME).is_file()
    has_lreview = (run_dir / cli._LEVER_REVIEW_NAME).is_file()
    if has_design != has_lreview:
        missing = cli._LEVER_REVIEW_NAME if has_design else cli._LEVER_DESIGN_NAME
        raise ValueError(f"incomplete lever stage: missing artifact: {missing}")
    lever_design = None
    lever_review = None
    if has_design:
        lever_design = _optional_json(cli, run_dir, cli._LEVER_DESIGN_NAME)
        lever_review = _optional_json(cli, run_dir, cli._LEVER_REVIEW_NAME)

    manifest = None
    if (run_dir / "manifest.json").is_file():
        manifest = cli._load_frozen_json(run_dir, "manifest.json")

    loaded_names = [name for _pid, name, _data in passes]
    if search_field is not None:
        loaded_names.append(cli._SEARCH_FIELD_NAME)
    if portfolio is not None:
        loaded_names.append("portfolio.json")
    loaded_names.extend(loaded_dev_names)
    loaded_names.extend(loaded_rev_names)
    if comparison is not None:
        loaded_names.append(comparison[0])
    if lever_design is not None:
        loaded_names.append(cli._LEVER_DESIGN_NAME)
        loaded_names.append(cli._LEVER_REVIEW_NAME)
    if manifest is not None:
        loaded_names.append("manifest.json")

    extras = []
    for p in sorted(run_dir.iterdir(), key=lambda x: x.name):
        if not p.is_file() or not p.name.endswith(".json") or p.name.endswith(".meta.json"):
            continue
        if p.name in loaded_names:
            continue
        if not _is_known_stage_name(p.name):
            extras.append(p.name)
    extra_docs = []
    for name in extras:
        extra_docs.append((name, cli._load_frozen_json(run_dir, name)))

    if not passes and portfolio is None and not developments and not reviews:
        raise ValueError("no stage artifacts to render")

    has_search = bool(passes)
    has_port = portfolio is not None
    has_dev = bool(developments)
    has_review = bool(reviews)

    next_move = portfolio.get("next_reasoning_move") if isinstance(portfolio, dict) else None
    is_intentional_terminal = (
        isinstance(portfolio, dict)
        and portfolio.get("route") == "AUTO"
        and next_move in ("GATHER_INFORMATION", "PRESERVE_ONLY")
    )

    if has_review:
        missing_next = None
        complete = True
    elif is_intentional_terminal:
        missing_next = None
        complete = True
    elif has_dev:
        missing_next = "Critic"
        complete = False
    elif has_port:
        missing_next = "Deep"
        complete = False
    elif has_search:
        missing_next = "Portfolio"
        complete = False
    else:
        missing_next = "Search"
        complete = False

    route = None
    if isinstance(portfolio, dict):
        route = portfolio.get("route")
    if isinstance(route, str) and route.strip():
        route_s = route.strip()
        if route_s == "FORGE":
            route_s = "BONK"
    else:
        route_s = "unknown"
    header_shape = route_s if complete else f"{route_s} · incomplete"

    auto_target = None
    if isinstance(portfolio, dict):
        raw_t = portfolio.get("auto_target")
        if isinstance(raw_t, dict) and raw_t.get("target_id"):
            auto_target = raw_t

    terminal_state = None
    if is_intentional_terminal:
        terminal_state = next_move
    else:
        for _n, rev in reviews:
            ts = rev.get("terminal_state")
            if isinstance(ts, str) and ts.strip():
                terminal_state = ts.strip()
                break
    metas = []
    timestamps = []
    run_ids = []
    for name in loaded_names:
        if not name.endswith(".json"):
            continue
        meta = _load_meta(cli, run_dir, name)
        if isinstance(meta, dict):
            metas.append((name, meta))
            ts = meta.get("timestamp")
            if isinstance(ts, str) and ts.strip():
                timestamps.append(ts.strip())
            rid = meta.get("run_id")
            if isinstance(rid, str) and rid.strip():
                run_ids.append(rid.strip())

    dirname = run_dir.name
    fallback_id = dirname[4:] if dirname.startswith("run-") else dirname
    run_id = run_ids[0] if run_ids else fallback_id
    timestamp = sorted(timestamps)[0] if timestamps else None

    model = harness = commit = skill_hash = None
    accounting = None
    if isinstance(manifest, dict):
        if isinstance(manifest.get("model"), str) and manifest["model"].strip():
            model = manifest["model"].strip()
        if isinstance(manifest.get("harness"), str) and manifest["harness"].strip():
            harness = manifest["harness"].strip()
        for key in ("repo_commit", "commit"):
            val = manifest.get(key)
            if isinstance(val, str) and val.strip():
                commit = val.strip()
                break
        sh = manifest.get("skill_hash")
        if isinstance(sh, str) and sh.strip():
            skill_hash = sh.strip()
        acc = manifest.get("accounting")
        if isinstance(acc, dict):
            accounting = acc

    hashes = []
    for name in loaded_names:
        if name.endswith(".json") and name != "manifest.json":
            digest = _sha_text(run_dir, name)
            if digest:
                hashes.append((name, digest))
    hashes.sort()
    loaded_names = sorted(set(loaded_names))

    return {
        "cli": cli,
        "run_dir": run_dir,
        "passes": passes,
        "cand_index": cand_index,
        "search_field": search_field,
        "portfolio": portfolio,
        "p_map": p_map,
        "developments": developments,
        "reviews": reviews,
        "comparison": comparison,
        "lever_design": lever_design,
        "lever_review": lever_review,
        "manifest": manifest,
        "accounting": accounting,
        "extra_docs": extra_docs,
        "complete": complete,
        "missing_next": missing_next,
        "route": route_s,
        "header_shape": header_shape,
        "auto_target": auto_target,
        "terminal_state": terminal_state,
        "run_id": run_id,
        "timestamp": timestamp,
        "model": model,
        "harness": harness,
        "commit": commit,
        "skill_hash": skill_hash,
        "metas": metas,
        "hashes": hashes,
        "loaded_names": loaded_names,
    }


def _acc_value(accounting, key, missing):
    if not isinstance(accounting, dict) or key not in accounting:
        return missing
    val = accounting[key]
    if val is None:
        return missing
    return str(val)


def _count_candidates(view) -> int:
    n = 0
    for _pid, _name, data in view["passes"]:
        cands = data.get("candidates") or []
        if isinstance(cands, list):
            n += sum(1 for c in cands if isinstance(c, dict))
    return n


def _dl(rows) -> str:
    parts = ['<dl class="facts">']
    for label, value in rows:
        parts.append(f"<dt>{_e(label)}</dt><dd>{value}</dd>")
    parts.append("</dl>")
    return "\n".join(parts)


def _missing_stage(stage_id: str, title: str, reason: str) -> str:
    return (
        f'<section id="{_e(stage_id)}" class="stage missing">'
        f"<h2>{_e(title)}</h2>"
        f'<p class="gap">{_prose(reason)}</p>'
        "</section>\n"
    )


def _render_header(view) -> str:
    term = view["terminal_state"] or "not reached"
    rows = [
        ("Route / shape", _e(view["header_shape"])),
        ("Run ID", f'<span class="tech">{_e(view["run_id"])}</span>'),
        (
            "Timestamp",
            _e(view["timestamp"]) if view["timestamp"] else _e("not recorded"),
        ),
        ("Model / provider", _e(view["model"] or "not recorded")),
        ("Terminal state", f'<span class="state">{_e(term)}</span>'),
    ]
    return (
        '<header id="top">'
        '<p class="kicker">Prism run</p>'
        f"<h1>{_e(view['header_shape'])}</h1>"
        f"{_dl(rows)}"
        "</header>\n"
    )


def _render_summary(view) -> str:
    at = view["auto_target"]
    term = view["terminal_state"] or "not reached"
    if at:
        selected = f"{at.get('target_type', '')} {at.get('target_id', '')}".strip()
    elif term in ("GATHER_INFORMATION", "PRESERVE_ONLY"):
        selected = f"none ({term})"
    else:
        selected = "none / not reached"
    acc = view["accounting"]
    n_p = len(view["p_map"])
    bundles = []
    if isinstance(view["portfolio"], dict):
        bundles = [b for b in (view["portfolio"].get("bundles") or []) if isinstance(b, dict)]
    rows = [
        ("Selected target", _e(selected)),
        ("Terminal state", f'<span class="state">{_e(term)}</span>'),
        ("Visible Perspectives", _e(str(n_p))),
        ("Bundles", _e(str(len(bundles)))),
    ]
    if isinstance(acc, dict):
        if "semantic_stage_count" in acc:
            rows.append(("Semantic stages", _e(str(acc["semantic_stage_count"]))))
        if "host_inference_count" in acc:
            rows.append(("Host inferences", _e(str(acc["host_inference_count"]))))
        if "input_tokens" in acc:
            rows.append(("Total input tokens", _e(str(acc["input_tokens"]))))
        if "output_tokens" in acc:
            rows.append(("Total output tokens", _e(str(acc["output_tokens"]))))
        if _COST_KEY in acc:
            rows.append(("Estimated cost", _e(str(acc[_COST_KEY]))))
    return (
        '<section id="summary" class="stage summary">'
        "<h2>What came out</h2>"
        f"{_dl(rows)}"
        "</section>\n"
    )


def _render_task(view) -> str:
    return (
        '<section id="task" class="stage task">'
        "<h2>Task</h2>"
        f"<p>{_prose(view['task'])}</p>"
        "</section>\n"
    )


def _render_perspectives(view) -> str:
    p_map = view["p_map"]
    if not p_map:
        if view["portfolio"] is None:
            return _missing_stage(
                "perspectives", "Perspectives", "Perspectives: not reached."
            )
        return (
            '<section id="perspectives" class="stage perspectives">'
            "<h2>Perspectives</h2>"
            "<p>No promoted Perspectives.</p>"
            "</section>\n"
        )
    cli = view["cli"]
    index = view["cand_index"]
    inv = {}
    for ref, pid in p_map.items():
        inv.setdefault(pid, []).append(ref)
    chunks = [
        '<section id="perspectives" class="stage perspectives">',
        "<h2>Perspectives</h2>",
    ]
    for pid in sorted(inv, key=cli._p_sort_key):
        refs = sorted(inv[pid], key=cli._ref_sort_key)
        ref = refs[0]
        cand = _try_candidate(cli, ref, index)
        title = cli._c_title(cand) if cand else "(untitled candidate)"
        thesis = ""
        core = {}
        epi = {}
        if cand:
            core = cand.get("semantic_core") or {}
            if isinstance(core, dict) and isinstance(core.get("claim"), str):
                thesis = core["claim"]
            epi = cand.get("epistemics") or {}
        chunks.append(
            f'<details open class="perspective" id="{_e(_aid("perspective", pid))}">'
            f'<summary><span class="pid">{_e(pid)}</span> — {_e(title)}</summary>'
            '<div class="detail-body">'
            f"<p><strong>Source.</strong> {_e(', '.join(refs))}</p>"
            "<p><strong>Status.</strong> KEEP</p>"
        )
        if thesis.strip():
            chunks.append(f"<p><strong>Thesis.</strong> {_prose(thesis)}</p>")
        if isinstance(core, dict):
            for label, field in _CORE_FIELDS:
                if field == "claim":
                    continue
                val = core.get(field)
                if isinstance(val, str) and val.strip():
                    chunks.append(f"<p><strong>{_e(label)}.</strong> {_prose(val)}</p>")
        if isinstance(epi, dict) and epi:
            parts = [
                f"{k}: {', '.join(v)}"
                for k, v in sorted(epi.items())
                if isinstance(v, list) and v
            ]
            if parts:
                chunks.append(f"<p><strong>Epistemics.</strong> {_e('; '.join(parts))}</p>")
        chunks.append("</div></details>")
    info_req = view["portfolio"].get("information_request") if isinstance(view["portfolio"], dict) else None
    if isinstance(info_req, dict):
        chunks.append('<details open class="perspective"><summary>Information Gathering Request</summary><div class="detail-body">')
        mode = info_req.get("mode")
        if mode:
            chunks.append(f"<p><strong>Mode.</strong> {_e(mode)}</p>")
        missing = info_req.get("missing_information")
        if missing:
            chunks.append(f"<p><strong>Missing information.</strong> {_prose(missing)}</p>")
        why = info_req.get("why_it_changes_route")
        if why:
            chunks.append(f"<p><strong>Why it changes route.</strong> {_prose(why)}</p>")
        qs = info_req.get("questions") or []
        if qs:
            chunks.append("<p><strong>Questions.</strong></p><ul>")
            for q in qs:
                chunks.append(f"<li>{_prose(q)}</li>")
            chunks.append("</ul>")
        obs = info_req.get("suggested_observation")
        if obs:
            chunks.append(f"<p><strong>Suggested observation.</strong> {_prose(obs)}</p>")
        chunks.append("</div></details>")
    chunks.append("</section>\n")
    return "\n".join(chunks)


def _member_anchor(view, ref: str) -> str:
    p_id = view["p_map"].get(ref)
    if p_id:
        return (
            f'<a href="#{_e(_aid("perspective", p_id))}">{_e(p_id)}</a>'
            f' <span class="cid">({_e(ref)})</span>'
        )
    cli = view["cli"]
    cand = _try_candidate(cli, ref, view["cand_index"])
    title = cli._c_title(cand) if cand else ref
    return f"{_e(ref)} ({_e(title)})"


def _render_bundles(view) -> str:
    portfolio = view["portfolio"]
    if portfolio is None:
        return _missing_stage("bundles", "Bundles", "Bundles: not reached.")
    bundles = [b for b in (portfolio.get("bundles") or []) if isinstance(b, dict)]
    if not bundles:
        return (
            '<section id="bundles" class="stage bundles">'
            "<h2>Bundles</h2><p>No bundles recorded.</p></section>\n"
        )
    chunks = ['<section id="bundles" class="stage bundles"><h2>Bundles</h2>']
    for b in bundles:
        bid = b.get("bundle_id") or "B?"
        members = [m for m in (b.get("member_refs") or []) if isinstance(m, str)]
        member_html = ", ".join(_member_anchor(view, m) for m in members)
        member_names = ", ".join(view["p_map"].get(m, m) for m in members)
        title = b.get("title") or member_names or bid
        chunks.append(
            f'<details class="bundle" id="{_e(_aid("bundle", bid))}">'
            f'<summary><span class="bid">{_e(bid)}</span> — {_e(title)}</summary>'
            '<div class="detail-body">'
            f"<p><strong>Members.</strong> {member_html}</p>"
        )
        roles = b.get("member_roles") or {}
        if isinstance(roles, dict) and members:
            role_bits = []
            for m in members:
                role = roles.get(m)
                if isinstance(role, str) and role.strip():
                    role_bits.append(f"{_member_anchor(view, m)}: {_e(role)}")
            if role_bits:
                chunks.append(
                    "<p><strong>Member roles.</strong> " + "; ".join(role_bits) + "</p>"
                )
        for label, field in _BUNDLE_FIELDS:
            val = b.get(field)
            if isinstance(val, str) and val.strip():
                chunks.append(f"<p><strong>{_e(label)}.</strong> {_prose(val)}</p>")
        ablation = b.get("member_ablation") or {}
        if isinstance(ablation, dict) and members:
            abl_bits = []
            for m in members:
                val = ablation.get(m)
                if isinstance(val, str) and val.strip():
                    abl_bits.append(f"{_member_anchor(view, m)}: {_prose(val)}")
            if abl_bits:
                chunks.append(
                    "<p><strong>Member ablation.</strong> "
                    + " | ".join(abl_bits)
                    + "</p>"
                )
        chunks.append("</div></details>")
    chunks.append("</section>\n")
    return "\n".join(chunks)


def _render_developed_model(model: dict) -> str:
    bits = []
    thesis = model.get("thesis")
    if isinstance(thesis, str) and thesis.strip():
        bits.append(f"<p><strong>Thesis.</strong> {_prose(thesis)}</p>")
    synthesis = model.get("synthesis")
    if isinstance(synthesis, str) and synthesis.strip():
        bits.append(f"<p><strong>Synthesis.</strong> {_prose(synthesis)}</p>")
    chain = [s for s in (model.get("mechanism_chain") or []) if isinstance(s, str)]
    if chain:
        bits.append("<h4>Mechanism / structural chain</h4><ol>")
        bits.extend(f"<li>{_prose(step)}</li>" for step in chain)
        bits.append("</ol>")
    dynamics = model.get("dynamics")
    if isinstance(dynamics, str) and dynamics.strip():
        bits.append(f"<p><strong>Dynamics.</strong> {_prose(dynamics)}</p>")
    contributions = model.get("member_contributions")
    if isinstance(contributions, dict) and contributions:
        bits.append("<h4>Member contributions</h4><ul>")
        for k in sorted(contributions):
            bits.append(f"<li>{_e(k)}: {_prose(contributions[k])}</li>")
        bits.append("</ul>")
    implications = [i for i in (model.get("implications") or []) if isinstance(i, str)]
    if implications:
        bits.append("<h4>Implications</h4><ul>")
        bits.extend(f"<li>{_prose(i)}</li>" for i in implications)
        bits.append("</ul>")
    preds = [
        p for p in (model.get("predictions_or_observables") or []) if isinstance(p, str)
    ]
    if preds:
        bits.append("<h4>Predictions / observables</h4><ul>")
        bits.extend(f"<li>{_prose(p)}</li>" for p in preds)
        bits.append("</ul>")
    claims = [c for c in (model.get("load_bearing_claims") or []) if isinstance(c, dict)]
    if claims:
        bits.append("<h4>Load-bearing claims</h4><ul>")
        for c in claims:
            status = c.get("epistemic_status") or "?"
            claim = c.get("claim") or ""
            bits.append(
                f"<li><strong>{_prose(claim)}</strong> ({_e(status)})"
                f" — role: {_prose(c.get('role_in_model', ''))};"
                f" weakened/refuted by: {_prose(c.get('what_would_weaken_or_refute', ''))}"
                "</li>"
            )
        bits.append("</ul>")
    breaks = [b for b in (model.get("break_conditions") or []) if isinstance(b, str)]
    if breaks:
        bits.append("<h4>Break conditions</h4><ul>")
        bits.extend(f"<li>{_prose(b)}</li>" for b in breaks)
        bits.append("</ul>")
    tensions = [t for t in (model.get("unresolved_tensions") or []) if isinstance(t, str)]
    if tensions:
        bits.append("<h4>Unresolved tensions</h4><ul>")
        bits.extend(f"<li>{_prose(t)}</li>" for t in tensions)
        bits.append("</ul>")
    debt = [d for d in (model.get("evidence_debt") or []) if isinstance(d, str)]
    if debt:
        bits.append("<h4>Evidence debt</h4><ul>")
        bits.extend(f"<li>{_prose(d)}</li>" for d in debt)
        bits.append("</ul>")
    comp_standing = model.get("comparative_standing")
    if isinstance(comp_standing, dict):
        bits.append("<h4>Comparative standing</h4><ul>")
        for label, field in (
            ("Rival reference", "rival_ref"),
            ("Material difference", "material_difference"),
            ("Selected target advantage", "selected_target_advantage"),
            ("Rival advantage or parity", "rival_advantage_or_parity"),
            ("Unresolved competition", "unresolved_competition"),
        ):
            val = comp_standing.get(field)
            if isinstance(val, str) and val.strip():
                bits.append(f"<li>{_e(label)}: {_prose(val)}</li>")
        bits.append("</ul>")

    delta = model.get("development_delta")
    if isinstance(delta, dict):
        bits.append("<h4>Development delta</h4>")
        summary = delta.get("summary")
        if summary:
            bits.append(f"<p><strong>Summary:</strong> {_prose(summary)}</p>")
        for label, cat in (
            ("New load-bearing claims", "new_load_bearing_claims"),
            ("Strengthened claims", "strengthened_claims"),
            ("New causal mechanisms", "new_causal_arrows_or_mechanisms"),
            ("Material imports", "material_imports"),
            ("Scope expansions", "scope_expansions"),
        ):
            items = delta.get(cat) or []
            if items:
                bits.append(f"<p><strong>{_e(label)}:</strong></p><ul>")
                bits.extend(f"<li>{_prose(x)}</li>" for x in items)
                bits.append("</ul>")
    return "\n".join(bits)


def _render_deep(view) -> str:
    if not view["developments"]:
        if view.get("terminal_state") in ("GATHER_INFORMATION", "PRESERVE_ONLY"):
            reason = f"Deep: not reached (run terminated at Portfolio with {view['terminal_state']})."
        elif view["missing_next"] == "Deep":
            reason = "Deep: not reached. Missing next stage after Portfolio."
        else:
            reason = "Deep: not reached."
        return _missing_stage("deep", "Developed model", reason)
    chunks = ['<section id="deep" class="stage deep"><h2>Developed model</h2>']
    for name, dev in view["developments"]:
        target = dev.get("target") if isinstance(dev.get("target"), dict) else {}
        tid = target.get("target_id") or ""
        lock = dev.get("identity_lock") or {}
        title = ""
        if isinstance(lock, dict) and isinstance(lock.get("title"), str):
            title = lock["title"].strip()
        heading = f"Target {tid}" + (f" — {title}" if title else "")
        if len(view["developments"]) > 1:
            heading = f"{heading} ({name})"
        model = dev.get("developed_model") or {}
        if not isinstance(model, dict):
            model = {}
        chunks.append(f"<h3>{_e(heading)}</h3>")
        if isinstance(lock, dict):
            for label, field in _LOCK_FIELDS:
                val = lock.get(field)
                if isinstance(val, str) and val.strip():
                    chunks.append(f"<p><strong>Identity {label.lower()}.</strong> {_prose(val)}</p>")
        chunks.append(_render_developed_model(model))
    chunks.append("</section>\n")
    return "\n".join(chunks)


def _render_one_review(rev: dict) -> str:
    bits = []
    terminal = rev.get("terminal_state")
    verified = rev.get("identity_verified")
    term_line = f"Terminal recommendation: {_e(terminal)}" if terminal else ""
    if isinstance(verified, bool):
        yn = "yes" if verified else "no"
        term_line = (term_line + f" (identity verified: {yn})").strip()
    if term_line:
        bits.append(f"<p><strong>{term_line}</strong></p>")
    rationale = rev.get("verdict_rationale")
    if isinstance(rationale, str) and rationale.strip():
        bits.append(
            f"<p><strong>Terminal recommendation.</strong> {_prose(rationale)}</p>"
        )
    counter = rev.get("independent_countermodel")
    if isinstance(counter, str) and counter.strip():
        bits.append(
            f"<p><strong>Independent countermodel.</strong> {_prose(counter)}</p>"
        )
    cheapest = rev.get("cheapest_discriminating_test")
    if isinstance(cheapest, str) and cheapest.strip():
        bits.append(f"<p><strong>Discriminating test.</strong> {_prose(cheapest)}</p>")
    main_attack = rev.get("main_attack")
    if isinstance(main_attack, str) and main_attack.strip():
        bits.append(f"<p><strong>Main attack.</strong> {_prose(main_attack)}</p>")
    defect = rev.get("load_bearing_defect")
    if isinstance(defect, str) and defect.strip():
        bits.append(f"<p><strong>Load-bearing defect.</strong> {_prose(defect)}</p>")
    coverage = rev.get("coverage_mismatch")
    if isinstance(coverage, str) and coverage.strip():
        bits.append(f"<p><strong>Coverage mismatch.</strong> {_prose(coverage)}</p>")
    reassessment = [
        r for r in (rev.get("load_bearing_reassessment") or []) if isinstance(r, dict)
    ]
    if reassessment:
        bits.append("<h4>Load-bearing claim reassessment</h4><ul>")
        for r in reassessment:
            bits.append(
                f"<li>{_prose(r.get('claim', ''))} "
                f"({_e(r.get('critic_epistemic_status', '?'))})</li>"
            )
        bits.append("</ul>")
    findings = rev.get("findings")
    if isinstance(findings, dict):
        finding_bits = []
        for label, field in (
            ("Cross-field contradictions", "cross_field_contradictions"),
            ("Unsupported specificity", "unsupported_specificity"),
            ("Epistemic laundering", "epistemic_laundering"),
        ):
            items = [x for x in (findings.get(field) or []) if isinstance(x, str)]
            for x in items:
                finding_bits.append(f"<li>{_e(label)}: {_prose(x)}</li>")
        unresolved = findings.get("unresolved_load_bearing_contradiction")
        if unresolved is True:
            finding_bits.append(
                "<li>Unresolved load-bearing contradiction: yes</li>"
            )
        elif unresolved is False:
            finding_bits.append(
                "<li>Unresolved load-bearing contradiction: no</li>"
            )
        blockers = findings.get("readiness_blockers") or []
        blocker_details = findings.get("readiness_blocker_details") or {}
        if blockers:
            for b in blockers:
                detail = blocker_details.get(b, "")
                if detail:
                    finding_bits.append(f"<li>Readiness blocker <strong>{_e(b)}</strong>: {_prose(detail)}</li>")
                else:
                    finding_bits.append(f"<li>Readiness blocker <strong>{_e(b)}</strong></li>")
        for label, field in (
            ("Identity drift", "identity_drift"),
            ("Cost relocation", "cost_relocation"),
            ("Coverage mismatch", "coverage_mismatch"),
        ):
            val = findings.get(field)
            if isinstance(val, str) and val.strip():
                finding_bits.append(f"<li>{_e(label)}: {_prose(val)}</li>")
        skeleton = findings.get("round_trip_skeleton")
        if isinstance(skeleton, str) and skeleton.strip():
            finding_bits.append(f"<li>Round-trip skeleton: {_prose(skeleton)}</li>")
        member_abl = findings.get("member_ablation")
        if isinstance(member_abl, str) and member_abl.strip():
            finding_bits.append(
                f"<li>Member ablation assessment: {_prose(member_abl)}</li>"
            )
        if finding_bits:
            bits.append("<h4>Findings</h4><ul>")
            bits.extend(finding_bits)
            bits.append("</ul>")
    debt = [d for d in (rev.get("evidence_debt") or []) if isinstance(d, str)]
    if debt:
        bits.append("<h4>Critic evidence debt</h4><ul>")
        bits.extend(f"<li>{_prose(d)}</li>" for d in debt)
        bits.append("</ul>")
    inquiry = rev.get("inquiry_program")
    if isinstance(inquiry, dict):
        bits.append("<h4>Inquiry program</h4><ul>")
        clm = inquiry.get("current_leading_models") or []
        if clm:
            bits.append(f"<li><strong>Leading models:</strong> {_prose(', '.join(clm))}</li>")
        uq = inquiry.get("unresolved_questions") or []
        if uq:
            bits.append("<li><strong>Unresolved questions:</strong><ul>")
            for q in uq:
                bits.append(f"<li>{_prose(q)}</li>")
            bits.append("</ul></li>")
        slr = inquiry.get("strongest_live_rival")
        if slr:
            bits.append(f"<li><strong>Strongest live rival:</strong> {_prose(slr)}</li>")
        rtwcm = inquiry.get("result_that_would_change_model")
        if rtwcm:
            bits.append(f"<li><strong>Result that would change model:</strong> {_prose(rtwcm)}</li>")
        sr = inquiry.get("stop_rule")
        if sr:
            bits.append(f"<li><strong>Stop rule:</strong> {_prose(sr)}</li>")
        bits.append("</ul>")
    return "\n".join(bits)


def _developed_target_label(view) -> str:
    at = view["auto_target"]
    if at and at.get("target_id"):
        return str(at.get("target_id"))
    for _n, dev in view["developments"]:
        target = dev.get("target") if isinstance(dev.get("target"), dict) else {}
        if target.get("target_id"):
            return str(target["target_id"])
    return "developed target"


def _render_critic(view) -> str:
    if not view["reviews"] and view["comparison"] is None:
        if view.get("terminal_state") in ("GATHER_INFORMATION", "PRESERVE_ONLY"):
            reason = f"Critic: not reached (run terminated at Portfolio with {view['terminal_state']})."
        elif view["missing_next"] == "Critic":
            reason = "Critic: not reached. Missing next stage after Deep."
        elif view["missing_next"] == "Deep":
            reason = "Critic: not reached. Missing next stage after Portfolio."
        else:
            reason = "Critic: not reached."
        return _missing_stage("critic", "Critic", reason)
    chunks = ['<section id="critic" class="stage critic"><h2>Critic</h2>']
    before = _developed_target_label(view)
    for name, rev in view["reviews"]:
        if len(view["reviews"]) > 1:
            chunks.append(f"<h3>{_e(name)}</h3>")
        chunks.append(_render_one_review(rev))
        verdict = rev.get("terminal_state") or "not recorded"
        chunks.append(
            '<aside class="gate">'
            "<h4>Gate transition</h4>"
            f"<p>Before Critic: developed target {_e(before)}</p>"
            f'<p>Critic verdict: <span class="state">{_e(verdict)}</span></p>'
            f'<p>Terminal state: <span class="state">{_e(verdict)}</span></p>'
            "</aside>"
        )
    chunks.append("</section>\n")
    return "\n".join(chunks)


def _render_lever(view) -> str:
    if view["lever_design"] is None:
        if view.get("terminal_state") in ("GATHER_INFORMATION", "PRESERVE_ONLY"):
            reason = f"LEVER: not reached (run terminated at Portfolio with {view['terminal_state']})."
        elif view["complete"]:
            reason = "LEVER artifacts not present."
            ts = view["terminal_state"]
            if ts and ts != "MODEL_READY":
                reason = (
                    f"LEVER artifacts not present. Recorded terminal state: {ts}."
                )
        else:
            reason = "LEVER: not reached."
        return _missing_stage("lever", "LEVER", reason)
    design = view["lever_design"]
    review = view["lever_review"] or {}
    chunks = ['<section id="lever" class="stage lever"><h2>LEVER</h2>']
    outcome = review.get("outcome")
    if isinstance(outcome, str) and outcome.strip():
        chunks.append(f"<p><strong>Outcome.</strong> {_e(outcome)}</p>")
    rationale = review.get("verdict_rationale")
    if isinstance(rationale, str) and rationale.strip():
        chunks.append(f"<p>{_prose(rationale)}</p>")
    verdict_by = {}
    for v in review.get("verdicts") or []:
        if isinstance(v, dict) and isinstance(v.get("lever_id"), str):
            verdict_by[v["lever_id"]] = v.get("verdict")
    levers = [l for l in (design.get("levers") or []) if isinstance(l, dict)]
    for lev in levers:
        lid = lev.get("lever_id") or "?"
        verdict = verdict_by.get(lid)
        suffix = f" ({verdict})" if verdict else ""
        chunks.append(f"<h3>{_e(lid)}{_e(suffix)}</h3>")
        for label, field in _LEVER_FIELDS:
            val = lev.get(field)
            if isinstance(val, str) and val.strip():
                chunks.append(f"<p><strong>{_e(label)}.</strong> {_prose(val)}</p>")
    chunks.append("</section>\n")
    return "\n".join(chunks)


def _render_final(view) -> str:
    if not view["complete"]:
        return (
            '<section id="final" class="stage final">'
            "<h2>Final result</h2>"
            '<div class="gap-notice">'
            "Final: not reached. Incomplete run; no terminal synthesis invented."
            "</div>"
            "</section>\n"
        )
    at = view["auto_target"] or {}
    tid = at.get("target_id") or _developed_target_label(view)
    title = ""
    for _n, dev in view["developments"]:
        lock = dev.get("identity_lock") or {}
        if isinstance(lock, dict) and isinstance(lock.get("title"), str):
            title = lock["title"].strip()
            if title:
                break
    selected = f"{tid}" + (f" — {title}" if title else "")
    term = view["terminal_state"] or "not recorded"
    if term in ("GATHER_INFORMATION", "PRESERVE_ONLY"):
        chunks = [
            '<section id="final" class="stage final"><h2>Final result</h2>',
            f"<p><strong>Selected:</strong> none ({_e(term)})</p>",
            f'<p><strong>Terminal state:</strong> <span class="state">{_e(term)}</span></p>',
        ]
        port = view.get("portfolio") or {}
        rat = port.get("next_reasoning_rationale")
        if rat:
            chunks.append(f"<p><strong>Rationale:</strong> {_prose(rat)}</p>")
        if term == "GATHER_INFORMATION":
            info = port.get("information_request") or {}
            mode = info.get("mode")
            missing = info.get("missing_information")
            why = info.get("why_it_changes_route")
            if mode:
                chunks.append(f"<p><strong>Information mode:</strong> {_e(mode)}</p>")
            if missing:
                chunks.append(f"<p><strong>Missing information:</strong> {_prose(missing)}</p>")
            if why:
                chunks.append(f"<p><strong>Why it changes route:</strong> {_prose(why)}</p>")
            qs = info.get("questions") or []
            if qs:
                chunks.append("<p><strong>Questions for user:</strong></p><ul>")
                for q in qs:
                    chunks.append(f"<li>{_prose(q)}</li>")
                chunks.append("</ul>")
            obs = info.get("suggested_observation")
            if obs:
                chunks.append(f"<p><strong>Suggested observation:</strong> {_prose(obs)}</p>")
            chunks.append("<p><strong>Honest stop:</strong> GATHER_INFORMATION — information requested before deep development; no further primitives executed.</p>")
        else:
            chunks.append("<p><strong>Honest stop:</strong> PRESERVE_ONLY — field preserved without deep development; no further primitives executed.</p>")
        chunks.append("</section>\n")
        return "\n".join(chunks)

    chunks = [
        '<section id="final" class="stage final"><h2>Final result</h2>',
        f"<p><strong>Selected:</strong> {_e(selected)}</p>",
        f'<p><strong>Terminal state:</strong> <span class="state">{_e(term)}</span></p>',
    ]
    if view["lever_review"] is not None:
        outcome = view["lever_review"].get("outcome")
        chunks.append(f"<p><strong>Lever:</strong> {_e(outcome)}</p>")
    else:
        chunks.append("<p><strong>Lever:</strong> not present</p>")

    if term in ("NEED_EVIDENCE", "RETURN_TO_EXPLORE"):
        chunks.append(
            f"<p><strong>Honest stop:</strong> {_e(term)}. "
            "No further primitives executed.</p>"
        )
    # Truthful check for dedicated post-Critic final synthesis artifact
    final_doc = None
    for name in ("final.json", "synthesis.json", "result.json"):
        for extra_name, doc in view.get("extra_docs") or []:
            if extra_name == name:
                final_doc = doc
                break
        if final_doc:
            break

    if final_doc and isinstance(final_doc, dict):
        syn = final_doc.get("synthesis") or final_doc.get("final_answer") or final_doc.get("text")
        if syn:
            chunks.append(f"<p><strong>Post-Critic synthesis:</strong> {_prose(syn)}</p>")
    else:
        chunks.append(
            '<div class="gap-notice">'
            "<strong>W1 content notice:</strong> No dedicated reader-facing post-Critic final synthesis "
            "is recorded in this frozen bundle (W1 data/content gap)."
            "</div>"
        )
    chunks.append("</section>\n")
    return "\n".join(chunks)


def _render_economics(view) -> str:
    acc = view["accounting"]
    if acc is None:
        return (
            '<section id="economics" class="stage economics">'
            "<h2>Run cost</h2>"
            "<p>Accounting instrumentation not recorded in run manifest.</p>"
            "<p>Stage-wise usage: not recorded</p>"
            "</section>\n"
        )
    rows = [
        ("Semantic stages", _acc_value(acc, "semantic_stage_count", "not recorded")),
        ("Host inferences", _acc_value(acc, "host_inference_count", "not recorded")),
        ("Repairs", _acc_value(acc, "model_repair_count", "not recorded")),
        ("Retries", _acc_value(acc, "checkpoint_retry_count", "not recorded")),
        ("Input tokens", _acc_value(acc, "input_tokens", "unavailable")),
        ("Output tokens", _acc_value(acc, "output_tokens", "unavailable")),
        ("Cache-read tokens", _acc_value(acc, "cache_read_tokens", "unavailable")),
        ("Cache-write tokens", _acc_value(acc, "cache_write_tokens", "unavailable")),
        ("Candidate bytes", _acc_value(acc, "candidate_bytes", "not recorded")),
        ("Development bytes", _acc_value(acc, "development_bytes", "not recorded")),
        ("Estimated cost", _acc_value(acc, _COST_KEY, "unavailable")),
    ]
    extra = []
    if isinstance(acc, dict):
        known = set(_ALLOWED_DISPLAY) | set(_TOKEN_KEYS) | {
            _COST_KEY,
            "stage_wise",
            "stage_wise_usage",
            "stage_usage",
        }
        for key in sorted(acc):
            if key not in known:
                extra.append((key, acc[key]))
    body = _dl((lab, _e(val)) for lab, val in rows)
    if extra:
        body += "<h3>Other recorded counters</h3>"
        body += _dl((_e(k), _e(v)) for k, v in extra)
    stage_line = "<p>Stage-wise usage: not recorded</p>"
    if isinstance(acc, dict):
        for key in ("stage_wise", "stage_wise_usage", "stage_usage"):
            if key in acc and acc[key] not in (None, "", [], {}):
                dumped = json.dumps(acc[key], ensure_ascii=False, indent=2, sort_keys=True)
                stage_line = (
                    "<p>Stage-wise usage:</p>"
                    f"<pre>{_e(dumped)}</pre>"
                )
                break
    return (
        '<section id="economics" class="stage economics">'
        "<h2>Run cost</h2>"
        f"{body}"
        f"{stage_line}"
        "</section>\n"
    )


_CSS = """
:root {
  --bg: #faf9f6;
  --fg: #1a1a1a;
  --muted: #666666;
  --line: #dedbd2;
  --card: #ffffff;
  --chip-bg: #f0eee8;
  --chip-fg: #333333;
}
* {
  box-sizing: border-box;
}
html {
  scroll-behavior: auto;
}
body {
  margin: 0;
  padding: 2.5rem 1.5rem 6rem;
  background: var(--bg);
  color: var(--fg);
  font-family: "Iosevka", "JetBrains Mono", "IBM Plex Mono", "SFMono-Regular", "SF Mono", "Fira Code", "Cascadia Mono", "Liberation Mono", monospace;
  font-size: 17px;
  line-height: 1.6;
  font-variant-ligatures: none;
  font-feature-settings: "liga" 0, "calt" 0;
}
main,
.reader-shell {
  width: min(100% - 48px, 980px);
  margin-inline: auto;
}
h1, h2, h3, h4, h5, h6 {
  font-family: inherit;
  font-weight: 600;
  line-height: 1.25;
  color: var(--fg);
}
h1 {
  font-size: 1.75rem;
  margin: 0.25rem 0 1rem;
}
h2 {
  font-size: 1.35rem;
  margin: 0 0 0.75rem;
}
h3 {
  font-size: 1.12rem;
  margin: 1.25rem 0 0.5rem;
}
h4 {
  font-size: 1.0rem;
  margin: 1rem 0 0.4rem;
}
p {
  margin: 0.6rem 0;
}
a {
  color: var(--fg);
  text-decoration: underline;
  text-underline-offset: 2px;
}
.kicker {
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-size: 0.75rem;
  color: var(--muted);
  margin: 0 0 0.25rem;
}
.tech, .cid, .pid, .bid {
  font-family: inherit;
  font-size: 0.9em;
  background: var(--chip-bg);
  color: var(--chip-fg);
  padding: 0.1em 0.35em;
  border-radius: 2px;
}
.state {
  font-weight: 600;
}
header {
  border-bottom: 2px solid var(--line);
  padding-bottom: 1.5rem;
  margin-bottom: 2rem;
}
.stage {
  margin: 2.25rem 0;
  padding-bottom: 2rem;
  border-bottom: 1px solid var(--line);
}
.stage:last-of-type {
  border-bottom: none;
}
.stage.summary,
.stage.economics,
.box {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 3px;
  padding: 1.25rem;
}
.stage.missing {
  color: var(--muted);
  border: 1px dashed var(--line);
  padding: 1rem 1.25rem;
  border-radius: 3px;
  background: transparent;
}
.gap-notice {
  background: var(--chip-bg);
  border: 1px solid var(--line);
  border-radius: 3px;
  padding: 0.75rem 1rem;
  margin: 0.75rem 0;
  font-size: 0.92rem;
  color: var(--muted);
}
dl.facts {
  display: grid;
  grid-template-columns: 14rem 1fr;
  gap: 0.35rem 1rem;
  margin: 0.5rem 0;
  font-size: 0.95rem;
}
dl.facts dt {
  color: var(--muted);
}
dl.facts dd {
  margin: 0;
}
nav.toc {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 3px;
  padding: 1rem 1.25rem;
  margin: 1.5rem 0 2rem;
}
nav.toc h2 {
  font-size: 0.85rem;
  margin: 0 0 0.6rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--muted);
}
nav.toc ol {
  margin: 0;
  padding-left: 1.25rem;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 0.35rem 1rem;
}
nav.toc li {
  font-size: 0.9rem;
}
.toolbar {
  margin: 1rem 0;
  display: flex;
  gap: 0.6rem;
  align-items: center;
}
.toolbar button {
  font-family: inherit;
  font-size: 0.85rem;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 3px;
  padding: 0.35rem 0.75rem;
  cursor: pointer;
  color: var(--fg);
}
.toolbar button:hover {
  background: var(--chip-bg);
}
details {
  margin: 0.5rem 0;
  border: 1px solid var(--line);
  border-radius: 3px;
  background: var(--card);
}
summary {
  cursor: pointer;
  padding: 0.6rem 0.85rem;
  font-weight: 600;
  user-select: none;
  outline: none;
}
summary:hover {
  background: var(--chip-bg);
}
details[open] > summary {
  border-bottom: 1px solid var(--line);
}
.detail-body {
  padding: 0.85rem 1rem;
}
article.perspective,
article.bundle {
  border-top: 1px solid var(--line);
  padding-top: 0.75rem;
  margin-top: 0.75rem;
}
aside.gate {
  border: 1px solid var(--line);
  background: var(--card);
  border-radius: 3px;
  padding: 0.85rem 1rem;
  margin-top: 1.25rem;
}
pre {
  background: var(--chip-bg);
  padding: 0.75rem 1rem;
  border-radius: 3px;
  overflow-x: auto;
  font-size: 0.88rem;
  border: 1px solid var(--line);
}
.back {
  margin-top: 2.5rem;
  font-size: 0.9rem;
}
footer.reader-footer {
  margin-top: 3rem;
  padding-top: 1rem;
  border-top: 1px solid var(--line);
  font-size: 0.85rem;
  color: var(--muted);
}
@media (max-width: 768px) {
  body {
    padding: 1rem 1rem 4rem;
  }
  main, .reader-shell {
    width: 100%;
  }
  dl.facts {
    grid-template-columns: 1fr;
    gap: 0.15rem;
  }
  nav.toc ol {
    grid-template-columns: 1fr;
  }
}
@media print {
  body { background: #fff; color: #000; padding: 0; }
  main, .reader-shell { width: 100%; max-width: none; }
  nav.toc, .toolbar, .back { display: none; }
  details { border: none; }
  details > *:not(summary) { display: block !important; }
  .stage, header { break-inside: avoid; border: none; }
}
""".strip()


def _toc() -> str:
    items = [
        ("#task", "Task"),
        ("#summary", "What came out"),
        ("#final", "Final result"),
        ("#deep", "Developed model"),
        ("#perspectives", "Perspectives"),
        ("#bundles", "Bundles"),
        ("#critic", "Critic"),
        ("#lever", "LEVER"),
        ("#economics", "Run cost"),
    ]
    lis = "".join(f'<li><a href="{href}">{_e(label)}</a></li>' for href, label in items)
    return f'<nav class="toc" id="toc"><h2>Contents</h2><ol>{lis}</ol></nav>\n'


def _toolbar() -> str:
    return (
        '<div class="toolbar" id="js-toolbar" hidden>'
        '<button type="button" id="expand-all">Expand all</button>'
        '<button type="button" id="collapse-all">Collapse all</button>'
        '<a href="#top">Back to top</a>'
        "</div>\n"
    )


_JS = """
(function () {
  var bar = document.getElementById("js-toolbar");
  if (bar) bar.removeAttribute("hidden");
  function setOpen(v) {
    var nodes = document.querySelectorAll("details");
    for (var i = 0; i < nodes.length; i++) nodes[i].open = v;
  }
  var ex = document.getElementById("expand-all");
  var cl = document.getElementById("collapse-all");
  if (ex) ex.onclick = function () { setOpen(true); };
  if (cl) cl.onclick = function () { setOpen(false); };
})();
""".strip()


def _build_html(view) -> str:
    parts = [
        "<!DOCTYPE html>\n",
        '<html lang="en">\n',
        "<head>\n",
        '<meta charset="utf-8">\n',
        f"<title>{_e('Prism run ' + view['run_id'] + ' — ' + view['header_shape'])}</title>\n",
        "<style>\n",
        _CSS,
        "\n</style>\n",
        "</head>\n",
        "<body>\n",
        '<main class="reader-shell">\n',
        _render_header(view),
        _toc(),
        _toolbar(),
        _render_task(view),
        _render_summary(view),
        _render_final(view),
        _render_deep(view),
        _render_perspectives(view),
        _render_bundles(view),
        _render_critic(view),
        _render_lever(view),
        _render_economics(view),
        '<p class="back"><a href="#top">Back to top</a></p>\n',
        f'<footer class="reader-footer"><p>Prism run <span class="tech">{_e(view["run_id"])}</span> · {_e(view["timestamp"] or "not recorded")}</p></footer>\n',
        "</main>\n",
        "<script>\n",
        _JS,
        "\n</script>\n",
        "</body>\n",
        "</html>\n",
    ]
    return "".join(parts)


def render_run_html(run_dir_str: str, task, output_path: str) -> int:
    cli = _bundle()
    run_dir = Path(run_dir_str)
    if not run_dir.is_dir():
        cli._die(f"run directory does not exist: {run_dir_str}")

    view = _load_run(run_dir)
    view["task"] = _resolve_task(run_dir, task)

    html_text = _build_html(view)
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(html_text, encoding="utf-8")
    print(f"RENDER_HTML_OK {out_file}")

    reader_script = Path(__file__).resolve().parent / "pizm-reader-server"
    if reader_script.is_file():
        try:
            root_dir = run_dir.parent.resolve()
            res = subprocess.run(
                [sys.executable, str(reader_script), "ensure", "--root", str(root_dir)],
                capture_output=True,
                text=True,
                timeout=5.0,
            )
            if res.returncode == 0:
                base_url = res.stdout.strip().splitlines()[-1].rstrip("/")
                print(f"Reader: {base_url}/run/{run_dir.name}/")
            else:
                print(f"Reader: file://{out_file.resolve()} (local reader server inactive)")
        except Exception:
            print(f"Reader: file://{out_file.resolve()} (local reader server inactive)")
    else:
        print(f"Reader: file://{out_file.resolve()}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: pizm_render_html.py <run_dir> [task] [output_path]", file=sys.stderr)
        sys.exit(2)
    r_dir = sys.argv[1]
    t_val = sys.argv[2] if len(sys.argv) > 2 else None
    o_val = sys.argv[3] if len(sys.argv) > 3 else str(Path(r_dir) / "run.html")
    sys.exit(render_run_html(r_dir, t_val, o_val))
