#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Intelligence Analyzer
------------------------------
ساخت نقشه قابل اتکای پروژه برای استفاده به عنوان Context در گفتگوهای جدید AI.

بدون وابستگی خارجی؛ Python 3.10+
خروجی‌ها:
  PROJECT_CONTEXT.md
  project_context.json

اجرا:
  python project_analyzer.py
  python project_analyzer.py --root /path/to/project
  python project_analyzer.py --root . --max-file-size 1500000
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
import hashlib
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

VERSION = "2.0.0"

DEFAULT_IGNORES = {
    ".git", ".hg", ".svn", ".idea", ".vscode", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".next", ".nuxt", ".output", ".turbo",
    "node_modules", "venv", ".venv", "env", ".env", "dist", "build",
    "coverage", ".coverage", "htmlcov", "vendor", "target", "Pods",
    "DerivedData", ".gradle", ".terraform", ".serverless", "logs", "tmp",
    "temp", "migrations",  # migration files are numerous; use --include-migrations to include
}
SOURCE_EXTENSIONS = {
    ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue",
    ".svelte", ".html", ".css", ".scss", ".sass", ".less", ".sql", ".sh",
    ".go", ".rs", ".java", ".php", ".rb", ".yaml", ".yml", ".toml", ".ini",
    ".cfg", ".json", ".md", ".mdx", ".prisma", ".graphql", ".gql",
}
CONFIG_NAMES = {
    "pyproject.toml", "requirements.txt", "Pipfile", "Pipfile.lock",
    "poetry.lock", "uv.lock", "setup.py", "setup.cfg", "package.json",
    "pnpm-lock.yaml", "yarn.lock", "package-lock.json", "bun.lockb",
    "bun.lock", "tsconfig.json", "next.config.js", "next.config.ts",
    "vite.config.ts", "vite.config.js", "webpack.config.js", "manage.py",
    "Dockerfile", "docker-compose.yml", "compose.yml", "Makefile",
    "Procfile", "vercel.json", "netlify.toml", "nginx.conf",
    "pytest.ini", "tox.ini", ".python-version", ".nvmrc",
}
SECRET_KEY_RE = re.compile(
    r"(?i)(secret|password|passwd|token|api[_-]?key|private[_-]?key|"
    r"access[_-]?key|client[_-]?secret)"
)
ENV_ASSIGN_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")
URL_RE = re.compile(r"""(?:https?://[^\s"'`<>]+)""")
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}
DJANGO_FIELD_RE = re.compile(r"models\.([A-Za-z_][A-Za-z0-9_]*)")
TAILWIND_RE = re.compile(r"""(?:className|class)\s*=\s*(["'`])([\s\S]*?)\1""")

def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()

def safe_read(path: Path, max_bytes: int) -> tuple[str | None, str | None]:
    try:
        if path.stat().st_size > max_bytes:
            return None, f"file exceeds size limit ({path.stat().st_size} bytes)"
        raw = path.read_bytes()
        return raw.decode("utf-8-sig", errors="replace"), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"

def compact(value: Any, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= limit else text[:limit - 1] + "…"

def node_text(node: ast.AST | None) -> str:
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return type(node).__name__

def get_call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = get_call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""

def literal(node: ast.AST | None) -> Any:
    if node is None:
        return None
    try:
        return ast.literal_eval(node)
    except Exception:
        return node_text(node)

def args_info(args: ast.arguments) -> list[dict[str, str]]:
    result = []
    positional = list(args.posonlyargs) + list(args.args)
    defaults_start = len(positional) - len(args.defaults)
    for i, arg in enumerate(positional):
        item = {"name": arg.arg}
        if arg.annotation:
            item["type"] = node_text(arg.annotation)
        if i >= defaults_start:
            item["default"] = node_text(args.defaults[i - defaults_start])
        result.append(item)
    if args.vararg:
        result.append({"name": "*" + args.vararg.arg})
    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        item = {"name": arg.arg}
        if arg.annotation:
            item["type"] = node_text(arg.annotation)
        if default is not None:
            item["default"] = node_text(default)
        result.append(item)
    if args.kwarg:
        result.append({"name": "**" + args.kwarg.arg})
    return result

class PythonFileAnalyzer(ast.NodeVisitor):
    def __init__(self, source: str, path: str):
        self.source, self.path = source, path
        self.result: dict[str, Any] = {
            "path": path, "docstring": "", "imports": [], "classes": [],
            "functions": [], "routes": [], "models": [], "signals": [],
            "tasks": [], "calls": [], "syntax_error": None,
        }
        self.class_stack: list[str] = []
        self.function_stack: list[str] = []

    def analyze(self) -> dict[str, Any]:
        try:
            tree = ast.parse(self.source, filename=self.path, type_comments=True)
            self.result["docstring"] = ast.get_docstring(tree) or ""
            self.visit(tree)
        except Exception as exc:
            self.result["syntax_error"] = f"{type(exc).__name__}: {exc}"
        return self.result

    def visit_Import(self, node: ast.Import) -> None:
        for item in node.names:
            self.result["imports"].append({"module": item.name, "alias": item.asname, "line": node.lineno})

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.result["imports"].append({
            "module": "." * node.level + (node.module or ""),
            "names": [x.name for x in node.names], "line": node.lineno,
        })

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        bases = [node_text(x) for x in node.bases]
        decorators = [node_text(x) for x in node.decorator_list]
        info = {
            "name": node.name, "line": node.lineno, "end_line": getattr(node, "end_lineno", None),
            "bases": bases, "decorators": decorators, "docstring": ast.get_docstring(node) or "",
            "methods": [], "attributes": [], "nested_classes": [],
        }
        parent = self.class_stack[-1] if self.class_stack else None
        (self.result["classes"][-1]["nested_classes"] if self.result["classes"] and parent else []).append(node.name) if parent else None
        self.result["classes"].append(info)
        self.class_stack.append(node.name)
        for item in node.body:
            if isinstance(item, (ast.Assign, ast.AnnAssign)):
                targets = item.targets if isinstance(item, ast.Assign) else [item.target]
                for target in targets:
                    if isinstance(target, ast.Name):
                        value = item.value
                        info["attributes"].append({
                            "name": target.id,
                            "value": compact(node_text(value), 180) if value else "",
                            "line": item.lineno,
                        })
            self.visit(item)
        self.class_stack.pop()

    def _function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        decorators = [node_text(x) for x in node.decorator_list]
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                name = get_call_name(child)
                if name:
                    calls.append({"name": name, "line": getattr(child, "lineno", node.lineno)})
        info = {
            "name": node.name, "line": node.lineno, "end_line": getattr(node, "end_lineno", None),
            "async": isinstance(node, ast.AsyncFunctionDef), "class": self.class_stack[-1] if self.class_stack else None,
            "args": args_info(node.args), "returns": node_text(node.returns),
            "decorators": decorators, "docstring": ast.get_docstring(node) or "",
            "calls": calls[:100],
        }
        if self.class_stack:
            for cls in reversed(self.result["classes"]):
                if cls["name"] == self.class_stack[-1]:
                    cls["methods"].append(info)
                    break
        self.result["functions"].append(info)
        self.function_stack.append(node.name)
        for dec in decorators:
            match = re.search(r"(?:router|app|api)\.(get|post|put|patch|delete|options|head)\s*\((.*?)\)", dec, re.I)
            if match:
                path_match = re.search(r"""['"]([^'"]+)['"]""", match.group(2))
                self.result["routes"].append({
                    "method": match.group(1).upper(),
                    "path": path_match.group(1) if path_match else None,
                    "handler": node.name, "line": node.lineno, "framework": "FastAPI/Starlette-style",
                    "confidence": "static-pattern",
                })
        if any("receiver" in d or "task" in d or "shared_task" in d for d in decorators):
            self.result["tasks"].append({"name": node.name, "decorators": decorators, "line": node.lineno})
        self.function_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._function(node)
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._function(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = get_call_name(node.func)
        if name:
            self.result["calls"].append({"name": name, "line": node.lineno})
        # Django model field declarations
        if self.class_stack and name.startswith("models."):
            field = name.split(".")[-1]
            if field.endswith("Field"):
                cls = next((c for c in reversed(self.result["classes"]) if c["name"] == self.class_stack[-1]), None)
                if cls is not None:
                    field_name = None
                    # assignment target is handled by visit_Assign/AnnAssign below
                    self._last_model_field = {"field_type": field, "arguments": [node_text(x) for x in node.args],
                                              "keywords": {k.arg: node_text(k.value) for k in node.keywords if k.arg},
                                              "line": node.lineno}
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        if self.class_stack and isinstance(node.value, ast.Call):
            name = get_call_name(node.value.func)
            if name.startswith("models.") and name.split(".")[-1].endswith("Field"):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        model = next((c for c in reversed(self.result["classes"]) if c["name"] == self.class_stack[-1]), None)
                        if model is not None:
                            model.setdefault("model_fields", []).append({
                                "name": target.id, "field_type": name.split(".")[-1],
                                "arguments": [node_text(x) for x in node.value.args],
                                "options": {k.arg: node_text(k.value) for k in node.value.keywords if k.arg},
                                "line": node.lineno,
                            })
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if self.class_stack and isinstance(node.value, ast.Call):
            name = get_call_name(node.value.func)
            if name.startswith("models.") and name.split(".")[-1].endswith("Field") and isinstance(node.target, ast.Name):
                model = next((c for c in reversed(self.result["classes"]) if c["name"] == self.class_stack[-1]), None)
                if model is not None:
                    model.setdefault("model_fields", []).append({
                        "name": node.target.id, "field_type": name.split(".")[-1],
                        "arguments": [node_text(x) for x in node.value.args],
                        "options": {k.arg: node_text(k.value) for k in node.value.keywords if k.arg},
                        "line": node.lineno,
                    })
        self.generic_visit(node)

def classify_file(path: Path, root: Path) -> set[str]:
    p = rel(path, root).lower()
    name = path.name.lower()
    tags = set()
    if path.suffix == ".py":
        tags.add("python")
        if name == "models.py" or "/models/" in "/" + p: tags.add("django-model-candidate")
        if name in {"views.py", "viewsets.py"} or "/views/" in "/" + p: tags.add("django-view-candidate")
        if name in {"serializers.py"}: tags.add("serializer-candidate")
        if name in {"urls.py"}: tags.add("url-config")
        if name in {"admin.py"}: tags.add("django-admin")
        if name in {"tasks.py"}: tags.add("task-candidate")
        if name in {"services.py"} or "/services/" in "/" + p: tags.add("service-candidate")
        if "test" in name or "/tests/" in "/" + p: tags.add("test")
        if "router" in p or name in {"main.py", "api.py"}: tags.add("api-candidate")
    if path.suffix in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}:
        tags.add("javascript-typescript")
        if any(x in p for x in ("/app/", "/pages/")): tags.add("frontend-route-candidate")
        if "component" in p: tags.add("component-candidate")
        if "hook" in p: tags.add("hook-candidate")
        if "api" in p or "service" in p: tags.add("api-client-candidate")
        if "test" in p or "spec" in p: tags.add("test")
    if name in CONFIG_NAMES or name.endswith((".toml", ".ini", ".cfg")): tags.add("configuration")
    if name.startswith(".env"): tags.add("environment-template")
    if name in {"dockerfile", "docker-compose.yml", "compose.yml"}: tags.add("infrastructure")
    if path.suffix in {".md", ".mdx"}: tags.add("documentation")
    if path.suffix in {".sql", ".prisma"}: tags.add("database-schema")
    return tags

def parse_frontend(source: str, path: str) -> dict[str, Any]:
    imports = []
    for m in re.finditer(r"""(?:import|export)\s+(?:[\s\S]*?\s+from\s+)?['"]([^'"]+)['"]""", source):
        imports.append(m.group(1))
    exports = sorted(set(re.findall(r"\bexport\s+(?:default\s+)?(?:async\s+)?(?:function|class|const|let|var)\s+([A-Za-z_$][\w$]*)", source)))
    interfaces = sorted(set(re.findall(r"\b(?:export\s+)?interface\s+([A-Za-z_$][\w$]*)", source)))
    types = sorted(set(re.findall(r"\b(?:export\s+)?type\s+([A-Za-z_$][\w$]*)\s*=", source)))
    hooks = sorted(set(re.findall(r"\b(?:export\s+)?function\s+(use[A-Z]\w*)|\b(?:export\s+)?const\s+(use[A-Z]\w*)\s*=", source)))
    hooks = sorted({a or b for a, b in hooks})
    components = sorted(set(exports + re.findall(r"\bfunction\s+([A-Z][A-Za-z0-9_]*)\s*\(", source)))
    api_calls = []
    for m in re.finditer(r"""(?:fetch|axios\.(?:get|post|put|patch|delete)|client\.(?:get|post|put|patch|delete))\s*\(\s*(['"`])([^'"`]+)\1""", source):
        api_calls.append({"expression": m.group(0)[:220], "target": m.group(2), "line": source.count("\n", 0, m.start()) + 1})
    route_patterns = [
        (r"""(?:href|to)\s*=\s*['"]([^'"]+)['"]""", "link"),
        (r"""(?:path|route)\s*:\s*['"]([^'"]+)['"]""", "route-config"),
    ]
    routes = []
    for pattern, kind in route_patterns:
        for m in re.finditer(pattern, source):
            value = m.group(1)
            if value.startswith("/"):
                routes.append({"path": value, "kind": kind, "line": source.count("\n", 0, m.start()) + 1})
    tailwind = sorted({c for m in TAILWIND_RE.finditer(source) for c in m.group(2).split() if not "${" in c})
    return {
        "path": path, "imports": sorted(set(imports)), "exports": components,
        "interfaces": interfaces, "types": types, "hooks": hooks,
        "api_calls": api_calls, "route_references": routes,
        "tailwind_classes": tailwind,
        "line_count": source.count("\n") + 1,
    }

def redact_env_line(line: str) -> str:
    m = ENV_ASSIGN_RE.match(line)
    if not m:
        return compact(line, 180)
    key, value = m.groups()
    if SECRET_KEY_RE.search(key):
        return f"{key}=<REDACTED>"
    return f"{key}={compact(value, 100)}"

def detect_stack(files: list[dict[str, Any]], config_texts: dict[str, str]) -> list[str]:
    names = {Path(f["path"]).name.lower() for f in files}
    stack = set()
    if any(f["path"].endswith(".py") for f in files): stack.add("Python")
    if "manage.py" in names or any("django" in x.lower() for x in config_texts.values()): stack.add("Django (detected by markers)")
    if any("fastapi" in x.lower() for x in config_texts.values()): stack.add("FastAPI (detected by markers)")
    if any(Path(f["path"]).suffix in {".ts", ".tsx"} for f in files): stack.add("TypeScript")
    if any(Path(f["path"]).suffix in {".js", ".jsx", ".tsx"} for f in files): stack.add("JavaScript/React candidate")
    if any("next.config" in f["path"] for f in files): stack.add("Next.js (config detected)")
    if "package.json" in names: stack.add("Node.js ecosystem")
    if any(Path(f["path"]).suffix == ".go" for f in files): stack.add("Go")
    if any(Path(f["path"]).suffix == ".php" for f in files): stack.add("PHP")
    if any(Path(f["path"]).suffix == ".rs" for f in files): stack.add("Rust")
    if any("dockerfile" == Path(f["path"]).name.lower() for f in files): stack.add("Docker")
    return sorted(stack)

def build_tree(paths: list[str], max_depth: int = 5) -> str:
    tree: dict[str, Any] = {}
    for item in paths:
        parts = item.split("/")
        if len(parts) > max_depth:
            parts = parts[:max_depth] + ["…"]
        cur = tree
        for part in parts:
            cur = cur.setdefault(part, {})
    lines = []
    def walk(node: dict[str, Any], prefix: str = "") -> None:
        keys = sorted(node)
        for i, key in enumerate(keys):
            last = i == len(keys) - 1
            lines.append(prefix + ("└── " if last else "├── ") + key)
            walk(node[key], prefix + ("    " if last else "│   "))
    walk(tree)
    return "\n".join(lines)

def analyze_project(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    root = root.resolve()
    ignores = set(DEFAULT_IGNORES)
    if args.include_migrations:
        ignores.discard("migrations")
    files: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    python_data, frontend_data = [], []
    config_texts: dict[str, str] = {}
    env_vars: list[dict[str, str]] = []
    docs, sql_files = [], []
    total_bytes = 0

    for current, dirs, filenames in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in ignores and not d.startswith(".venv"))
        for filename in sorted(filenames):
            path = Path(current) / filename
            if path.resolve() == (root / "PROJECT_CONTEXT.md").resolve() or path.name == "project_context.json":
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size > args.max_file_size:
                errors.append({"path": rel(path, root), "error": f"skipped: {size} bytes exceeds max-file-size"})
                continue
            total_bytes += size
            tags = sorted(classify_file(path, root))
            is_text_candidate = (path.suffix.lower() in SOURCE_EXTENSIONS or path.name in CONFIG_NAMES
                                 or path.name.startswith(".env") or path.name.lower() in {"dockerfile", "makefile"})
            if not tags:
                tags = ["other-file"]
            item = {"path": rel(path, root), "size": size, "extension": path.suffix.lower(),
                    "tags": tags, "sha256": ""}
            files.append(item)
            if not is_text_candidate:
                continue
            content, error = safe_read(path, args.max_file_size)
            if error:
                errors.append({"path": item["path"], "error": error})
                continue
            assert content is not None
            item["sha256"] = hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()
            if path.suffix == ".py":
                parsed = PythonFileAnalyzer(content, item["path"]).analyze()
                python_data.append(parsed)
                if parsed.get("syntax_error"):
                    errors.append({"path": item["path"], "error": parsed["syntax_error"]})
            elif path.suffix.lower() in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}:
                frontend_data.append(parse_frontend(content, item["path"]))
            if "configuration" in tags or "environment-template" in tags:
                config_texts[item["path"]] = content[:30000]
            if "environment-template" in tags:
                for line in content.splitlines():
                    m = ENV_ASSIGN_RE.match(line)
                    if m:
                        env_vars.append({"file": item["path"], "entry": redact_env_line(line)})
            if "documentation" in tags:
                docs.append({"path": item["path"], "title": next((x.lstrip("# ").strip() for x in content.splitlines() if x.startswith("#")), "")})
            if "database-schema" in tags:
                sql_files.append(item["path"])

    # Build import/dependency index and approximate local edges.
    known_paths = {Path(f["path"]).with_suffix("").as_posix(): f["path"] for f in files}
    dependency_edges = []
    for entry in python_data:
        source_path = Path(entry["path"])
        source_module = source_path.with_suffix("").as_posix().replace("/", ".")
        for imp in entry["imports"]:
            module = imp["module"].lstrip(".")
            candidate = module.replace(".", "/")
            target = known_paths.get(candidate)
            if target:
                dependency_edges.append({"from": entry["path"], "to": target, "kind": "python-import", "confidence": "static"})
    for entry in frontend_data:
        base = Path(entry["path"]).parent
        for imp in entry["imports"]:
            if not imp.startswith("."):
                continue
            candidate_base = (base / imp)
            candidates = [candidate_base.with_suffix(ext) for ext in (".ts", ".tsx", ".js", ".jsx")]
            candidates += [candidate_base / ("index" + ext) for ext in (".ts", ".tsx", ".js", ".jsx")]
            target = next((p.as_posix() for p in candidates if (root / p).exists()), None)
            if target:
                dependency_edges.append({"from": entry["path"], "to": target, "kind": "frontend-import", "confidence": "static"})

    models = []
    all_routes = []
    python_classes = []
    for entry in python_data:
        for cls in entry["classes"]:
            python_classes.append({"path": entry["path"], **cls})
            if any("models.Model" in b or b.endswith(".Model") for b in cls["bases"]):
                models.append({"path": entry["path"], **cls})
        all_routes.extend({"file": entry["path"], **r} for r in entry["routes"])

    # Find Django URL declarations, view/serializer/service symbols and frontend API references.
    django_url_patterns = []
    for entry in python_data:
        if Path(entry["path"]).name == "urls.py":
            for call in entry["calls"]:
                if call["name"].split(".")[-1] in {"path", "re_path", "include"}:
                    django_url_patterns.append({"file": entry["path"], **call})
    symbol_index = defaultdict(list)
    for entry in python_data:
        for fn in entry["functions"]:
            symbol_index[fn["name"]].append(entry["path"])
        for cls in entry["classes"]:
            symbol_index[cls["name"]].append(entry["path"])

    tailwind_counts = Counter(c for entry in frontend_data for c in entry["tailwind_classes"])
    extensions = Counter(Path(f["path"]).suffix.lower() or "[no extension]" for f in files)
    tags_count = Counter(tag for f in files for tag in f["tags"])
    return {
        "meta": {
            "analyzer": "Project Intelligence Analyzer", "version": VERSION,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "project_root_name": root.name, "python_version": sys.version.split()[0],
            "analysis_mode": "static source analysis; project code was not executed",
        },
        "summary": {
            "file_count": len(files), "total_source_bytes": total_bytes,
            "python_file_count": len(python_data), "frontend_file_count": len(frontend_data),
            "model_count": len(models), "python_class_count": len(python_classes),
            "python_function_count": sum(len(x["functions"]) for x in python_data),
            "route_count": len(all_routes), "dependency_edge_count": len(dependency_edges),
            "error_count": len(errors),
        },
        "technology_stack": detect_stack(files, config_texts),
        "files": files, "directory_tree": build_tree([f["path"] for f in files], args.tree_depth),
        "python": python_data, "frontend": frontend_data,
        "django_models": models, "python_classes": python_classes,
        "detected_routes": all_routes, "django_url_declarations": django_url_patterns,
        "dependency_edges": dependency_edges, "symbol_index": dict(symbol_index),
        "config_files": sorted(config_texts), "environment_variables": env_vars,
        "documentation_files": docs, "database_schema_files": sql_files,
        "tailwind_top_classes": [{"class": k, "occurrences": v} for k, v in tailwind_counts.most_common(60)],
        "file_extensions": dict(extensions), "file_categories": dict(tags_count),
        "analysis_errors": errors,
    }

def md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").replace("`", "'")

def generate_markdown(data: dict[str, Any], max_items: int = 500) -> str:
    s, meta = data["summary"], data["meta"]
    out = [
        "# PROJECT CONTEXT",
        "",
        "> این فایل به‌صورت خودکار از سورس پروژه تولید شده است. اطلاعات استخراج‌شده از کد از فرضیات جدا شده‌اند.",
        f"> نسخه تحلیلگر: {meta['version']} | زمان تولید (UTC): {meta['generated_at_utc']}",
        f"> حالت تحلیل: {meta['analysis_mode']}",
        "",
        "## 1. خلاصه پروژه",
        f"- نام ریشه پروژه: `{meta['project_root_name']}`",
        f"- تعداد فایل‌های تحلیل‌شده: {s['file_count']}",
        f"- حجم فایل‌های خوانده‌شده: {s['total_source_bytes']:,} bytes",
        f"- فایل Python: {s['python_file_count']} | فایل Frontend: {s['frontend_file_count']}",
        f"- کلاس Python: {s['python_class_count']} | تابع: {s['python_function_count']}",
        f"- مدل‌های شناسایی‌شده: {s['model_count']} | Routeهای شناسایی‌شده: {s['route_count']}",
        f"- خطاها/فایل‌های تحلیل‌نشده: {s['error_count']}",
        "",
        "## 2. فناوری‌های شناسایی‌شده",
    ]
    out += [f"- {x}" for x in data["technology_stack"]] or ["- موردی با اطمینان کافی شناسایی نشد."]
    out += ["", "## 3. ساختار فایل‌ها و پوشه‌ها", "", "```text", data["directory_tree"] or "(empty)", "```",
            "", "## 4. تنظیمات و وابستگی‌های پروژه"]
    out += [f"- `{x}`" for x in data["config_files"]] or ["- فایل تنظیمات شناخته‌شده‌ای پیدا نشد."]
    if data["environment_variables"]:
        out += ["", "### متغیرهای محیطی شناسایی‌شده", "> مقدارهای حساس حذف شده‌اند."]
        out += [f"- `{x['file']}`: `{x['entry']}`" for x in data["environment_variables"][:max_items]]
    out += ["", "## 5. مدل‌های دیتابیس شناسایی‌شده"]
    if not data["django_models"]:
        out.append("- مدل Django مبتنی بر `models.Model` شناسایی نشد.")
    for model in data["django_models"][:max_items]:
        out.append(f"### `{model['name']}` — `{model['path']}:{model['line']}`")
        out.append(f"- ارث‌بری: {', '.join(model['bases']) or 'مشخص نیست'}")
        for field in model.get("model_fields", []):
            opts = ", ".join(f"{k}={v}" for k, v in field["options"].items())
            out.append(f"- `{field['name']}`: `{field['field_type']}` ({'; '.join(field['arguments'])}) {opts} [line {field['line']}]")
        if model.get("docstring"): out.append(f"- توضیح: {compact(model['docstring'], 300)}")
    out += ["", "## 6. کلاس‌ها و توابع Python"]
    for entry in data["python"]:
        if not entry["classes"] and not entry["functions"]:
            continue
        out.append(f"### `{entry['path']}`")
        for cls in entry["classes"]:
            out.append(f"- **class `{cls['name']}`** (line {cls['line']}) extends `{', '.join(cls['bases'])}`")
            for method in cls["methods"]:
                out.append(f"  - `{method['name']}({', '.join(a['name'] for a in method['args'])})` — line {method['line']}")
        for fn in entry["functions"]:
            if fn["class"] is None:
                out.append(f"- `{ 'async ' if fn['async'] else ''}def {fn['name']}({', '.join(a['name'] for a in fn['args'])})` — line {fn['line']}")
    out += ["", "## 7. API و Routeهای شناسایی‌شده"]
    if data["detected_routes"]:
        for route in data["detected_routes"][:max_items]:
            out.append(f"- **{route['method']} {route.get('path') or '[dynamic path]'}** → `{route['handler']}` در `{route['file']}:{route['line']}` ({route['framework']})")
    else:
        out.append("- Route با الگوهای استاتیک پشتیبانی‌شده شناسایی نشد. این به معنی نبود API نیست.")
    if data["django_url_declarations"]:
        out += ["", "### نشانه‌های URLConf جنگو"]
        out += [f"- `{x['file']}:{x['line']}` → `{x['name']}`" for x in data["django_url_declarations"][:max_items]]
    out += ["", "## 8. Frontend: صفحات، کامپوننت‌ها و ارتباط‌ها"]
    for entry in data["frontend"][:max_items]:
        if not (entry["exports"] or entry["interfaces"] or entry["api_calls"] or entry["route_references"]):
            continue
        out.append(f"### `{entry['path']}`")
        if entry["exports"]: out.append(f"- خروجی‌ها/کامپوننت‌های احتمالی: {', '.join(f'`{x}`' for x in entry['exports'])}")
        if entry["interfaces"]: out.append(f"- Interfaceها: {', '.join(f'`{x}`' for x in entry['interfaces'])}")
        if entry["types"]: out.append(f"- Typeها: {', '.join(f'`{x}`' for x in entry['types'])}")
        if entry["hooks"]: out.append(f"- Hookها: {', '.join(f'`{x}`' for x in entry['hooks'])}")
        if entry["api_calls"]:
            out.append("- فراخوانی‌های API:")
            out += [f"  - `{x['target']}` (line {x['line']})" for x in entry["api_calls"]]
        if entry["route_references"]:
            out.append("- مسیرهای ارجاع‌شده:")
            out += [f"  - `{x['path']}` (line {x['line']})" for x in entry["route_references"]]
        if entry["imports"]: out.append(f"- Importها: {', '.join(f'`{x}`' for x in entry['imports'][:30])}")
    out += ["", "## 9. گراف وابستگی‌های محلی"]
    out.append("> این ارتباط‌ها از importهای قابل resolve استخراج شده‌اند؛ وابستگی زمان اجرا ممکن است بیشتر باشد.")
    out += [f"- `{x['from']}` → `{x['to']}` ({x['kind']})" for x in data["dependency_edges"][:max_items]]
    if not data["dependency_edges"]: out.append("- ارتباط محلی قابل resolve شناسایی نشد.")
    out += ["", "## 10. فایل‌های مستندات و Schema"]
    out += [f"- مستندات: `{x['path']}`" + (f" — {x['title']}" if x["title"] else "") for x in data["documentation_files"]]
    out += [f"- فایل Schema/SQL: `{x}`" for x in data["database_schema_files"]]
    out += ["", "## 11. آمار ساختار"]
    out += [f"- `{k}`: {v}" for k, v in sorted(data["file_extensions"].items())]
    out += ["", "### کلاس‌های پرتکرار Tailwind"]
    out += [f"- `{x['class']}`: {x['occurrences']}" for x in data["tailwind_top_classes"][:40]]
    out += ["", "## 12. خطاها و محدودیت‌های تحلیل"]
    if data["analysis_errors"]:
        out += [f"- `{x['path']}`: {x['error']}" for x in data["analysis_errors"][:max_items]]
    else:
        out.append("- خطای خواندن یا Parse ثبت نشد.")
    out += [
        "",
        "## 13. راهنمای استفاده برای AI",
        "- این سند نقشه استاتیک سورس‌کد است، نه تضمین رفتار واقعی برنامه.",
        "- برای تغییر یک قابلیت، ابتدا مسیر فایل‌ها، نمادها و وابستگی‌های مرتبط را بررسی کن.",
        "- قبل از تغییر مدل یا API، تمام ارجاع‌های آن را در سورس جست‌وجو کن.",
        "- هرجا اطلاعات این سند کافی نیست، فایل‌های مرجع را مستقیماً بخوان؛ از حدس‌زدن خودداری کن.",
        "- اطلاعات دارای عبارت «احتمالی» یا «استاتیک» قطعی نیستند.",
        "",
        "## 14. مواردی که این نسخه تضمین نمی‌کند",
        "- اجرای برنامه، تحلیل رفتار واقعی، کشف کامل جریان Business Logic یا اثبات نبود باگ.",
        "- استخراج کامل URLهای Django، routerهای پویا، مسیرهای ساخته‌شده در زمان اجرا و APIهای غیرمستقیم.",
        "- حل کامل aliasهای TypeScript، importهای barrel، dynamic import و تمام syntaxهای JSX با Regex.",
        "- تولید ERD قطعی از migrationهای پیچیده، دیتابیس زنده یا مدل‌های سفارشی.",
        "- تشخیص قطعی کد مرده، امنیت یا پوشش تست بدون ابزار تخصصی و اجرای کنترل‌شده.",
        "",
    ]
    return "\n".join(out)

def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AI-ready project context documentation.")
    parser.add_argument("--root", default=".", help="Project root directory (default: current directory)")
    parser.add_argument("--output-md", default="PROJECT_CONTEXT.md")
    parser.add_argument("--output-json", default="project_context.json")
    parser.add_argument("--max-file-size", type=int, default=1_500_000, help="Maximum bytes per file")
    parser.add_argument("--tree-depth", type=int, default=7)
    parser.add_argument("--include-migrations", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"ERROR: project root does not exist: {root}", file=sys.stderr)
        return 2
    data = analyze_project(root, args)
    md_path = root / args.output_md
    json_path = root / args.output_json
    md_path.write_text(generate_markdown(data), encoding="utf-8")
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Project analysis completed.")
    print(f"Markdown: {md_path}")
    print(f"JSON:     {json_path}")
    print(f"Files: {data['summary']['file_count']} | Models: {data['summary']['model_count']} | "
          f"Routes: {data['summary']['route_count']} | Errors: {data['summary']['error_count']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
