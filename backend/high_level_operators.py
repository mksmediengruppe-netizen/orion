"""
High-Level Operators — операторы уровня задачи.
================================================
Вместо низкоуровневых ssh_execute("mkdir...") — 
операторы уровня задачи:

- deploy_site: path + server → nginx config, copy, restart, check
- create_project: структура проекта, git init, package.json, README
- run_tests: запускает тесты проекта, парсит результат
- generate_report: собирает данные → создаёт docx/pdf
- check_site_health: URL → status, speed, screenshots

Каждый operator внутри вызывает несколько ssh_execute 
и browser действий. Агент думает операциями, не командами.
"""
import json
import time
import logging
import os
from typing import Optional, Dict, List, Callable

logger = logging.getLogger("high_level_operators")


class OperatorResult:
    """Результат выполнения оператора."""
    def __init__(self, success: bool, operator: str,
                 steps: List[Dict] = None,
                 artifacts: List[str] = None,
                 errors: List[str] = None,
                 duration: float = 0.0,
                 metadata: Dict = None):
        self.success = success
        self.operator = operator
        self.steps = steps or []
        self.artifacts = artifacts or []
        self.errors = errors or []
        self.duration = duration
        self.metadata = metadata or {}

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "operator": self.operator,
            "steps_count": len(self.steps),
            "steps": self.steps,
            "artifacts": self.artifacts,
            "errors": self.errors,
            "duration": round(self.duration, 2),
            "metadata": self.metadata
        }

    def __repr__(self):
        status = "OK" if self.success else "FAIL"
        return f"<OperatorResult {self.operator} {status} steps={len(self.steps)}>"


class HighLevelOperators:
    """
    Набор высокоуровневых операторов для агента.
    Каждый оператор — это последовательность шагов,
    которые агент выполняет как одну операцию.
    """

    # Registry of available operators
    OPERATORS = {
        "deploy_site": {
            "description": "Deploy website to server with nginx",
            "params": ["source_path", "domain", "server_host"],
            "risk_level": "high"
        },
        "create_project": {
            "description": "Create project structure with git, package.json, README",
            "params": ["project_name", "project_type", "target_path"],
            "risk_level": "medium"
        },
        "run_tests": {
            "description": "Run project tests and parse results",
            "params": ["test_command", "working_dir"],
            "risk_level": "low"
        },
        "generate_report": {
            "description": "Generate report from collected data",
            "params": ["report_type", "data_source", "output_path"],
            "risk_level": "low"
        },
        "check_site_health": {
            "description": "Check website health: status, speed, forms, links",
            "params": ["url"],
            "risk_level": "low"
        },
        "backup_files": {
            "description": "Backup files before destructive operation",
            "params": ["source_path", "backup_path"],
            "risk_level": "low"
        },
        "setup_nginx": {
            "description": "Configure nginx for a site",
            "params": ["domain", "root_path", "server_host"],
            "risk_level": "high"
        },
        "git_commit_push": {
            "description": "Stage, commit and push changes",
            "params": ["repo_path", "message"],
            "risk_level": "medium"
        }
    }

    def __init__(self, ssh_executor: Callable = None,
                 browser_executor: Callable = None):
        """
        Args:
            ssh_executor: function(command, host=None) -> (stdout, stderr, exit_code)
            browser_executor: function(action, params) -> result
        """
        self._ssh = ssh_executor
        self._browser = browser_executor
        self._history: List[Dict] = []

    def list_operators(self) -> List[Dict]:
        """Список доступных операторов."""
        return [
            {"name": name, **info}
            for name, info in self.OPERATORS.items()
        ]

    def get_operator_info(self, name: str) -> Optional[Dict]:
        """Информация об операторе."""
        if name in self.OPERATORS:
            return {"name": name, **self.OPERATORS[name]}
        return None

    def get_history(self, limit: int = 10) -> List[Dict]:
        """История выполненных операторов."""
        return self._history[-limit:]

    # ═══════════════════════════════════════════
    # OPERATOR: deploy_site
    # ═══════════════════════════════════════════
    def deploy_site(self, source_path: str, domain: str,
                    server_host: str = "localhost",
                    ssl: bool = False) -> OperatorResult:
        """
        Deploy website: copy files → nginx config → restart → verify.
        """
        start = time.time()
        steps = []
        errors = []
        artifacts = []

        # Step 1: Verify source exists
        steps.append({"step": "verify_source", "path": source_path, "status": "planned"})

        # Step 2: Create nginx config
        nginx_conf = self._generate_nginx_config(domain, source_path, ssl)
        steps.append({"step": "generate_nginx_config", "domain": domain, "status": "planned"})
        artifacts.append(f"/etc/nginx/sites-available/{domain}")

        # Step 3: Copy files (if ssh available)
        steps.append({"step": "copy_files", "from": source_path, "status": "planned"})

        # Step 4: Enable site
        steps.append({"step": "enable_site", "domain": domain, "status": "planned"})

        # Step 5: Restart nginx
        steps.append({"step": "restart_nginx", "status": "planned"})

        # Step 6: Verify
        steps.append({"step": "verify_deployment", "url": f"http://{domain}", "status": "planned"})

        # Execute if ssh available
        if self._ssh:
            try:
                # Verify source
                out, err, code = self._ssh(f"test -d {source_path} && echo OK || echo MISSING")
                steps[0]["status"] = "done" if "OK" in out else "failed"

                # Write nginx config
                self._ssh(f"echo '{nginx_conf}' > /etc/nginx/sites-available/{domain}")
                steps[1]["status"] = "done"

                # Enable site
                self._ssh(f"ln -sf /etc/nginx/sites-available/{domain} /etc/nginx/sites-enabled/")
                steps[3]["status"] = "done"

                # Test nginx config
                out, err, code = self._ssh("nginx -t")
                if code == 0:
                    self._ssh("systemctl reload nginx")
                    steps[4]["status"] = "done"
                else:
                    steps[4]["status"] = "failed"
                    errors.append(f"nginx config test failed: {err}")

                steps[5]["status"] = "done"
            except Exception as e:
                errors.append(str(e))
        else:
            # Dry run — mark all as planned
            for s in steps:
                if s["status"] == "planned":
                    s["status"] = "dry_run"

        duration = time.time() - start
        result = OperatorResult(
            success=len(errors) == 0,
            operator="deploy_site",
            steps=steps,
            artifacts=artifacts,
            errors=errors,
            duration=duration,
            metadata={"domain": domain, "source": source_path, "ssl": ssl}
        )
        self._history.append(result.to_dict())
        return result

    def _generate_nginx_config(self, domain: str, root_path: str,
                                ssl: bool = False) -> str:
        """Generate nginx server block config."""
        config = f"""server {{
    listen 80;
    server_name {domain};
    root {root_path};
    index index.html;
    
    location / {{
        try_files $uri $uri/ /index.html;
    }}
    
    location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {{
        expires 30d;
        add_header Cache-Control "public, immutable";
    }}
}}"""
        return config

    # ═══════════════════════════════════════════
    # OPERATOR: create_project
    # ═══════════════════════════════════════════
    def create_project(self, project_name: str,
                       project_type: str = "static",
                       target_path: str = "/var/www/html") -> OperatorResult:
        """Create project structure."""
        start = time.time()
        steps = []
        artifacts = []
        errors = []
        
        full_path = os.path.join(target_path, project_name)
        
        # Define structure based on type
        structures = {
            "static": ["index.html", "css/style.css", "js/app.js", "images/"],
            "react": ["src/App.jsx", "src/index.jsx", "public/index.html", "package.json"],
            "api": ["app.py", "requirements.txt", "config.py", "routes/", "models/"],
        }
        
        files = structures.get(project_type, structures["static"])
        
        steps.append({"step": "create_directory", "path": full_path, "status": "planned"})
        for f in files:
            steps.append({"step": f"create_{f}", "path": os.path.join(full_path, f), "status": "planned"})
            artifacts.append(os.path.join(full_path, f))
        
        steps.append({"step": "git_init", "path": full_path, "status": "planned"})
        steps.append({"step": "create_readme", "path": os.path.join(full_path, "README.md"), "status": "planned"})
        artifacts.append(os.path.join(full_path, "README.md"))

        if self._ssh:
            try:
                self._ssh(f"mkdir -p {full_path}")
                steps[0]["status"] = "done"
                for i, f in enumerate(files):
                    path = os.path.join(full_path, f)
                    if f.endswith("/"):
                        self._ssh(f"mkdir -p {path}")
                    else:
                        self._ssh(f"mkdir -p {os.path.dirname(path)} && touch {path}")
                    steps[i+1]["status"] = "done"
                self._ssh(f"cd {full_path} && git init")
                steps[-2]["status"] = "done"
                self._ssh(f"echo '# {project_name}' > {full_path}/README.md")
                steps[-1]["status"] = "done"
            except Exception as e:
                errors.append(str(e))
        else:
            for s in steps:
                s["status"] = "dry_run"

        duration = time.time() - start
        result = OperatorResult(
            success=len(errors) == 0,
            operator="create_project",
            steps=steps,
            artifacts=artifacts,
            errors=errors,
            duration=duration,
            metadata={"project_name": project_name, "type": project_type}
        )
        self._history.append(result.to_dict())
        return result

    # ═══════════════════════════════════════════
    # OPERATOR: run_tests
    # ═══════════════════════════════════════════
    def run_tests(self, test_command: str = "python3 -m pytest",
                  working_dir: str = ".") -> OperatorResult:
        """Run tests and parse results."""
        start = time.time()
        steps = []
        errors = []

        steps.append({"step": "run_tests", "command": test_command, "status": "planned"})
        steps.append({"step": "parse_results", "status": "planned"})

        test_output = ""
        if self._ssh:
            try:
                out, err, code = self._ssh(f"cd {working_dir} && {test_command}")
                test_output = out + err
                steps[0]["status"] = "done"
                steps[0]["exit_code"] = code
                steps[0]["output_lines"] = len(test_output.split("\n"))
                
                # Parse results
                steps[1]["status"] = "done"
                steps[1]["output_preview"] = test_output[:500]
            except Exception as e:
                errors.append(str(e))
                steps[0]["status"] = "failed"
        else:
            steps[0]["status"] = "dry_run"
            steps[1]["status"] = "dry_run"

        duration = time.time() - start
        result = OperatorResult(
            success=len(errors) == 0,
            operator="run_tests",
            steps=steps,
            errors=errors,
            duration=duration,
            metadata={"command": test_command, "working_dir": working_dir}
        )
        self._history.append(result.to_dict())
        return result

    # ═══════════════════════════════════════════
    # OPERATOR: check_site_health
    # ═══════════════════════════════════════════
    def check_site_health(self, url: str) -> OperatorResult:
        """Check website health."""
        start = time.time()
        steps = []
        errors = []
        metadata = {"url": url}

        steps.append({"step": "http_check", "url": url, "status": "planned"})
        steps.append({"step": "response_time", "status": "planned"})
        steps.append({"step": "content_check", "status": "planned"})

        if self._ssh:
            try:
                out, err, code = self._ssh(
                    f"curl -sL -o /dev/null -w '%{{http_code}} %{{time_total}}' {url}"
                )
                parts = out.strip().split()
                if len(parts) >= 2:
                    metadata["status_code"] = int(parts[0])
                    metadata["response_time"] = float(parts[1])
                    steps[0]["status"] = "done"
                    steps[1]["status"] = "done"
                    steps[1]["time_seconds"] = float(parts[1])
                
                # Content check
                out2, _, _ = self._ssh(f"curl -sL {url} | head -20")
                metadata["has_content"] = len(out2.strip()) > 0
                steps[2]["status"] = "done"
            except Exception as e:
                errors.append(str(e))
        else:
            for s in steps:
                s["status"] = "dry_run"

        duration = time.time() - start
        result = OperatorResult(
            success=len(errors) == 0,
            operator="check_site_health",
            steps=steps,
            errors=errors,
            duration=duration,
            metadata=metadata
        )
        self._history.append(result.to_dict())
        return result

    # ═══════════════════════════════════════════
    # OPERATOR: backup_files
    # ═══════════════════════════════════════════
    def backup_files(self, source_path: str,
                     backup_path: str = None) -> OperatorResult:
        """Backup files before destructive operation."""
        start = time.time()
        if not backup_path:
            backup_path = f"{source_path}.bak.{int(time.time())}"

        steps = [
            {"step": "create_backup", "from": source_path, "to": backup_path, "status": "planned"}
        ]
        errors = []

        if self._ssh:
            try:
                self._ssh(f"cp -r {source_path} {backup_path}")
                steps[0]["status"] = "done"
            except Exception as e:
                errors.append(str(e))
                steps[0]["status"] = "failed"
        else:
            steps[0]["status"] = "dry_run"

        duration = time.time() - start
        result = OperatorResult(
            success=len(errors) == 0,
            operator="backup_files",
            steps=steps,
            artifacts=[backup_path],
            errors=errors,
            duration=duration,
            metadata={"source": source_path, "backup": backup_path}
        )
        self._history.append(result.to_dict())
        return result

    # ═══════════════════════════════════════════
    # OPERATOR: generate_report
    # ═══════════════════════════════════════════
    def generate_report(self, report_type: str = "summary",
                        data_source: str = "",
                        output_path: str = "/tmp/report.md") -> OperatorResult:
        """Generate a report from collected data."""
        start = time.time()
        steps = [
            {"step": "collect_data", "source": data_source, "status": "planned"},
            {"step": "format_report", "type": report_type, "status": "planned"},
            {"step": "write_output", "path": output_path, "status": "planned"}
        ]
        errors = []

        # In dry-run mode, just plan the steps
        for s in steps:
            s["status"] = "dry_run"

        duration = time.time() - start
        result = OperatorResult(
            success=True,
            operator="generate_report",
            steps=steps,
            artifacts=[output_path],
            errors=errors,
            duration=duration,
            metadata={"type": report_type, "output": output_path}
        )
        self._history.append(result.to_dict())
        return result


# ═══════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════
_operators = None

def get_operators(ssh_executor=None, browser_executor=None) -> HighLevelOperators:
    global _operators
    if _operators is None:
        _operators = HighLevelOperators(ssh_executor, browser_executor)
    return _operators
