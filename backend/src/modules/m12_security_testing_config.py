"""Módulo backlog #12: Configuração de Security Testing.

Fornece configurações e utilitários para execução de testes de segurança
no pipeline CI/CD e em ambiente local, incluindo:

- OWASP ZAP (Dynamic Application Security Testing - DAST)
- Bandit (Static Application Security Testing - SAST para Python)
- Safety (auditoria de dependências Python contra CVEs conhecidas)
- pip-audit (auditoria complementar de dependências)

Este módulo centraliza configurações, gera arquivos de configuração
e fornece comandos prontos para integração com CI/CD.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # backend/
REPORTS_DIR = PROJECT_ROOT / "reports" / "security"
CONFIG_DIR = PROJECT_ROOT / "config" / "security"


class SeverityLevel(str, Enum):
    """Níveis de severidade para classificação de achados de segurança."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ToolName(str, Enum):
    """Ferramentas de security testing suportadas."""

    BANDIT = "bandit"
    SAFETY = "safety"
    PIP_AUDIT = "pip-audit"
    OWASP_ZAP = "owasp-zap"


# ---------------------------------------------------------------------------
# Dataclasses de configuração
# ---------------------------------------------------------------------------


@dataclass
class BanditConfig:
    """Configuração para análise estática de segurança com Bandit.

    Bandit examina código Python em busca de padrões inseguros comuns,
    como uso de eval(), senhas hardcoded, SQL injection, etc.
    """

    targets: list[str] = field(default_factory=lambda: ["src/"])
    exclude_dirs: list[str] = field(
        default_factory=lambda: [".venv", "__pycache__", "tests", "migrations"]
    )
    severity_level: SeverityLevel = SeverityLevel.LOW
    confidence_level: SeverityLevel = SeverityLevel.LOW
    output_format: str = "json"
    output_file: str = "bandit_report.json"
    skips: list[str] = field(
        default_factory=lambda: [
            "B101",  # assert usado em testes — falso positivo comum
        ]
    )
    recursive: bool = True
    ini_config_name: str = ".bandit"

    def to_cli_args(self) -> list[str]:
        """Gera argumentos de linha de comando para execução do Bandit."""
        args = ["bandit"]

        if self.recursive:
            args.append("-r")

        args.extend(self.targets)

        if self.exclude_dirs:
            args.extend(["-x", ",".join(self.exclude_dirs)])

        severity_map = {
            SeverityLevel.LOW: "-ll",
            SeverityLevel.MEDIUM: "-ll",
            SeverityLevel.HIGH: "-lll",
            SeverityLevel.CRITICAL: "-lll",
        }
        args.append(severity_map.get(self.severity_level, "-l"))

        if self.skips:
            args.extend(["--skip", ",".join(self.skips)])

        report_path = REPORTS_DIR / self.output_file
        args.extend(["-f", self.output_format, "-o", str(report_path)])

        return args

    def generate_ini_config(self) -> str:
        """Gera conteúdo do arquivo .bandit (formato INI)."""
        lines = [
            "[bandit]",
            f"exclude = {','.join(self.exclude_dirs)}",
            f"skips = {','.join(self.skips)}",
            f"targets = {','.join(self.targets)}",
        ]
        return "\n".join(lines) + "\n"


@dataclass
class SafetyConfig:
    """Configuração para auditoria de dependências com Safety.

    Safety verifica as dependências Python instaladas contra um banco
    de dados de vulnerabilidades conhecidas (CVEs).
    """

    requirements_files: list[str] = field(
        default_factory=lambda: ["requirements.txt", "requirements-dev.txt"]
    )
    output_format: str = "json"
    output_file: str = "safety_report.json"
    continue_on_error: bool = True
    full_report: bool = True
    api_key: str | None = None  # Chave da API Safety (opcional, para DB completo)

    def to_cli_args(self) -> list[str]:
        """Gera argumentos de linha de comando para execução do Safety."""
        args = ["safety", "check"]

        for req_file in self.requirements_files:
            req_path = PROJECT_ROOT / req_file
            if req_path.exists():
                args.extend(["--file", str(req_path)])

        if self.full_report:
            args.append("--full-report")

        report_path = REPORTS_DIR / self.output_file
        args.extend(["--output", self.output_format])

        api_key = self.api_key or os.getenv("SAFETY_API_KEY")
        if api_key:
            args.extend(["--key", api_key])

        return args


@dataclass
class PipAuditConfig:
    """Configuração para auditoria de dependências com pip-audit.

    Complementa o Safety com verificação via banco de dados do PyPI Advisory.
    """

    requirements_files: list[str] = field(
        default_factory=lambda: ["requirements.txt"]
    )
    output_format: str = "json"
    output_file: str = "pip_audit_report.json"
    strict: bool = True
    desc: str = "on"  # Inclui descrição das vulnerabilidades
    fix: bool = False  # Não aplicar correções automaticamente

    def to_cli_args(self) -> list[str]:
        """Gera argumentos de linha de comando para execução do pip-audit."""
        args = ["pip-audit"]

        for req_file in self.requirements_files:
            req_path = PROJECT_ROOT / req_file
            if req_path.exists():
                args.extend(["-r", str(req_path)])

        args.extend(["-f", self.output_format])
        args.extend(["--desc", self.desc])

        if self.strict:
            args.append("--strict")

        report_path = REPORTS_DIR / self.output_file
        args.extend(["-o", str(report_path)])

        return args


@dataclass
class OwaspZapConfig:
    """Configuração para DAST (Dynamic Application Security Testing) com OWASP ZAP.

    OWASP ZAP realiza testes dinâmicos contra a aplicação em execução,
    identificando vulnerabilidades como XSS, SQL Injection, CSRF, etc.
    """

    target_url: str = "http://localhost:8000"
    api_key: str | None = None
    zap_docker_image: str = "ghcr.io/zaproxy/zaproxy:stable"
    scan_type: str = "baseline"  # baseline | full | api
    openapi_spec_url: str | None = None  # URL do OpenAPI spec para scan de API
    output_file: str = "zap_report.html"
    output_format: str = "html"
    rules_config_file: str = "zap_rules.conf"
    ajax_spider: bool = False
    max_duration_minutes: int = 10
    fail_on_risk: SeverityLevel = SeverityLevel.HIGH

    # Regras a ignorar (falsos positivos conhecidos para APIs REST)
    ignored_rules: list[str] = field(
        default_factory=lambda: [
            "10096",  # Timestamp Disclosure — comum em APIs REST
            "10055",  # CSP Header — gerenciado pelo Nginx/frontend
        ]
    )

    def to_docker_command(self) -> list[str]:
        """Gera comando Docker para execução do OWASP ZAP."""
        report_path = REPORTS_DIR / self.output_file
        rules_path = CONFIG_DIR / self.rules_config_file

        scan_scripts = {
            "baseline": "zap-baseline.py",
            "full": "zap-full-scan.py",
            "api": "zap-api-scan.py",
        }
        scan_script = scan_scripts.get(self.scan_type, "zap-baseline.py")

        cmd = [
            "docker",
            "run",
            "--rm",
            "--network=host",
            "-v",
            f"{REPORTS_DIR}:/zap/wrk:rw",
        ]

        if rules_path.exists():
            cmd.extend(["-v", f"{rules_path}:/zap/wrk/rules.conf:ro"])

        cmd.extend([
            self.zap_docker_image,
            scan_script,
            "-t",
            self.target_url,
            "-m",
            str(self.max_duration_minutes),
            "-r",
            self.output_file,
        ])

        if self.scan_type == "api" and self.openapi_spec_url:
            cmd.extend(["-f", "openapi"])

        if self.ajax_spider:
            cmd.append("-j")

        if rules_path.exists():
            cmd.extend(["-c", "rules.conf"])

        return cmd

    def generate_rules_config(self) -> str:
        """Gera arquivo de configuração de regras do ZAP.

        Formato: <rule_id>\tIGNORE\t(<descrição>)
        """
        lines = [
            "# Configuração de regras OWASP ZAP para Automação Jurídica Assistida",
            "# Formato: <rule_id>\t<ação>\t<descrição>",
            "# Ações: IGNORE, WARN, FAIL",
            "",
        ]
        for rule_id in self.ignored_rules:
            lines.append(f"{rule_id}\tIGNORE\t(Falso positivo conhecido)")

        return "\n".join(lines) + "\n"

    def get_openapi_scan_command(self) -> list[str]:
        """Gera comando para scan específico da API via OpenAPI spec."""
        spec_url = self.openapi_spec_url or f"{self.target_url}/openapi.json"

        cmd = [
            "docker",
            "run",
            "--rm",
            "--network=host",
            "-v",
            f"{REPORTS_DIR}:/zap/wrk:rw",
            self.zap_docker_image,
            "zap-api-scan.py",
            "-t",
            spec_url,
            "-f",
            "openapi",
            "-r",
            "zap_api_report.html",
            "-m",
            str(self.max_duration_minutes),
        ]

        return cmd


# ---------------------------------------------------------------------------
# Configuração agregada
# ---------------------------------------------------------------------------


@dataclass
class SecurityTestingConfig:
    """Configuração centralizada de todas as ferramentas de security testing.

    Agrega configurações de Bandit, Safety, pip-audit e OWASP ZAP,
    fornecendo métodos para geração de arquivos de configuração,
    execução de scans e geração de relatórios consolidados.
    """

    bandit: BanditConfig = field(default_factory=BanditConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    pip_audit: PipAuditConfig = field(default_factory=PipAuditConfig)
    owasp_zap: OwaspZapConfig = field(default_factory=OwaspZapConfig)
    fail_on_critical: bool = True
    reports_dir: Path = REPORTS_DIR
    config_dir: Path = CONFIG_DIR

    def ensure_directories(self) -> None:
        """Cria diretórios necessários para relatórios e configurações."""
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def generate_all_configs(self) -> dict[str, Path]:
        """Gera todos os arquivos de configuração das ferramentas.

        Returns:
            Dicionário mapeando nome da ferramenta ao caminho do arquivo gerado.
        """
        self.ensure_directories()
        generated: dict[str, Path] = {}

        # Bandit .bandit config
        bandit_path = PROJECT_ROOT / self.bandit.ini_config_name
        bandit_path.write_text(self.bandit.generate_ini_config(), encoding="utf-8")
        generated["bandit"] = bandit_path

        # ZAP rules config
        zap_rules_path = self.config_dir / self.owasp_zap.rules_config_file
        zap_rules_path.write_text(
            self.owasp_zap.generate_rules_config(), encoding="utf-8"
        )
        generated["owasp_zap"] = zap_rules_path

        return generated

    def get_ci_pipeline_config(self) -> dict[str, Any]:
        """Gera configuração para integração com pipeline CI/CD.

        Retorna um dicionário com os jobs de segurança prontos para
        serem integrados em GitHub Actions, GitLab CI ou similar.
        """
        return {
            "security_testing": {
                "description": "Pipeline de testes de segurança — Automação Jurídica Assistida",
                "stages": [
                    {
                        "name": "sast_bandit",
                        "tool": ToolName.BANDIT.value,
                        "description": "Análise estática de segurança do código Python",
                        "command": self.bandit.to_cli_args(),
                        "allow_failure": False,
                        "stage": "test",
                    },
                    {
                        "name": "dependency_safety",
                        "tool": ToolName.SAFETY.value,
                        "description": "Auditoria de vulnerabilidades em dependências (Safety)",
                        "command": self.safety.to_cli_args(),
                        "allow_failure": not self.fail_on_critical,
                        "stage": "test",
                    },
                    {
                        "name": "dependency_pip_audit",
                        "tool": ToolName.PIP_AUDIT.value,
                        "description": "Auditoria de vulnerabilidades em dependências (pip-audit)",
                        "command": self.pip_audit.to_cli_args(),
                        "allow_failure": not self.fail_on_critical,
                        "stage": "test",
                    },
                    {
                        "name": "dast_zap_baseline",
                        "tool": ToolName.OWASP_ZAP.value,
                        "description": "Scan dinâmico baseline com OWASP ZAP",
                        "command": self.owasp_zap.to_docker_command(),
                        "allow_failure": True,  # DAST pode ter falsos positivos
                        "stage": "security",
                        "requires": ["deploy_staging"],
                    },
                    {
                        "name": "dast_zap_api",
                        "tool": ToolName.OWASP_ZAP.value,
                        "description": "Scan dinâmico da API via OpenAPI spec",
                        "command": self.owasp_zap.get_openapi_scan_command(),
                        "allow_failure": True,
                        "stage": "security",
                        "requires": ["deploy_staging"],
                    },
                ],
            }
        }

    def generate_github_actions_workflow(self) -> str:
        """Gera workflow do GitHub Actions para security testing.

        Returns:
            Conteúdo YAML do workflow.
        """
        workflow = """# Gerado automaticamente por m12_security_testing_config.py
# Pipeline de Security Testing — Automação Jurídica Assistida
name: Security Testing

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    # Execução semanal para detectar novas CVEs
    - cron: '0 6 * * 1'

jobs:
  sast-bandit:
    name: "SAST — Bandit (Análise Estática)"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configurar Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Instalar Bandit
        run: pip install bandit[toml]

      - name: Executar Bandit
        run: |
          mkdir -p reports/security
          bandit -r src/ -x .venv,__pycache__,tests,migrations \\
            --skip {skips} \\
            -f json -o reports/security/bandit_report.json \\
            || true

      - name: Upload relatório Bandit
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: bandit-report
          path: reports/security/bandit_report.json

  dependency-audit:
    name: "Auditoria de Dependências"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configurar Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Instalar ferramentas
        run: pip install safety pip-audit

      - name: Instalar dependências do projeto
        run: pip install -e ".[dev]"

      - name: Executar Safety
        run: |
          mkdir -p reports/security
          safety check --output json > reports/security/safety_report.json || true
        env:
          SAFETY_API_KEY: ${{{{ secrets.SAFETY_API_KEY }}}}

      - name: Executar pip-audit
        run: |
          pip-audit -f json -o reports/security/pip_audit_report.json --desc on || true

      - name: Upload relatórios
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: dependency-audit-reports
          path: reports/security/

  dast-zap:
    name: "DAST — OWASP ZAP (Análise Dinâmica)"
    runs-on: ubuntu-latest
    needs: [sast-bandit]  # Executa após SAST
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4

      - name: Configurar Python e iniciar aplicação
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      # TODO: Adicionar step para iniciar a aplicação em modo de teste
      # Depende da configuração de docker-compose ou script de inicialização

      - name: OWASP ZAP Baseline Scan
        uses: zaproxy/action-baseline@v0.10.0
        with:
          target: '{target_url}'
          rules_file_name: 'config/security/zap_rules.conf'
          cmd_options: '-m {max_duration}'
        continue-on-error: true

      - name: Upload relatório ZAP
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: zap-report
          path: reports/security/
""".format(
            skips=",".join(self.bandit.skips),
            target_url=self.owasp_zap.target_url,
            max_duration=self.owasp_zap.max_duration_minutes,
        )
        return workflow


# ---------------------------------------------------------------------------
# Funções utilitárias de execução
# ---------------------------------------------------------------------------


def run_tool(
    tool: ToolName,
    config: SecurityTestingConfig | None = None,
    capture_output: bool = True,
) -> dict[str, Any]:
    """Executa uma ferramenta de security testing e retorna o resultado.

    Args:
        tool: Ferramenta a ser executada.
        config: Configuração de security testing. Se None, usa padrão.
        capture_output: Se True, captura stdout/stderr.

    Returns:
        Dicionário com status da execução, código de retorno e caminho do relatório.
    """
    if config is None:
        config = SecurityTestingConfig()

    config.ensure_directories()

    tool_configs = {
        ToolName.BANDIT: {
            "args": config.bandit.to_cli_args(),
            "report": config.reports_dir / config.bandit.output_file,
        },
        ToolName.SAFETY: {
            "args": config.safety.to_cli_args(),
            "report": config.reports_dir / config.safety.output_file,
        },
        ToolName.PIP_AUDIT: {
            "args": config.pip_audit.to_cli_args(),
            "report": config.reports_dir / config.pip_audit.output_file,
        },
        ToolName.OWASP_ZAP: {
            "args": config.owasp_zap.to_docker_command(),
            "report": config.reports_dir / config.owasp_zap.output_file,
        },
    }

    tool_cfg = tool_configs[tool]
    args: list[str] = tool_cfg["args"]
    report_path: Path = tool_cfg["report"]

    result: dict[str, Any] = {
        "tool": tool.value,
        "command": " ".join(args),
        "report_path": str(report_path),
        "return_code": -1,
        "success": False,
        "error": None,
    }

    try:
        proc = subprocess.run(
            args,
            capture_output=capture_output,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=600,  # 10 minutos de timeout
        )
        result["return_code"] = proc.returncode
        result["success"] = proc.returncode == 0

        if capture_output:
            result["stdout"] = proc.stdout
            result["stderr"] = proc.stderr

    except FileNotFoundError:
        result["error"] = (
            f"Ferramenta '{tool.value}' não encontrada. "
            f"Instale com: pip install {tool.value}"
        )
    except subprocess.TimeoutExpired:
        result["error"] = (
            f"Timeout ao executar '{tool.value}'. "
            f"Considere aumentar o limite de tempo."
        )
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"Erro inesperado ao executar '{tool.value}': {exc}"

    return result


def run_all_sast(
    config: SecurityTestingConfig | None = None,
) -> list[dict[str, Any]]:
    """Executa todas as ferramentas SAST e de auditoria de dependências.

    Não inclui OWASP ZAP (DAST) pois requer a aplicação em execução.

    Args:
        config: Configuração de security testing. Se None, usa padrão.

    Returns:
        Lista de resultados de cada ferramenta.
    """
    if config is None:
        config = SecurityTestingConfig()

    sast_tools = [ToolName.BANDIT, ToolName.SAFETY, ToolName.PIP_AUDIT]
    results = []

    for tool in sast_tools:
        print(f"\n{'='*60}")
        print(f"Executando {tool.value}...")
        print(f"{'='*60}")
        result = run_tool(tool, config)
        results.append(result)

        status = "✅ OK" if result["success"] else "❌ FALHA"
        print(f"Resultado: {status}")
        if result.get("error"):
            print(f"Erro: {result['error']}")

    return results


def generate_consolidated_report(
    results: list[dict[str, Any]],
    config: SecurityTestingConfig | None = None,
) -> Path:
    """Gera relatório consolidado de todos os scans de segurança.

    Args:
        results: Lista de resultados das ferramentas.
        config: Configuração de security testing.

    Returns:
        Caminho do relatório consolidado gerado.
    """
    if config is None:
        config = SecurityTestingConfig()

    config.ensure_directories()

    report = {
        "projeto": "Automação Jurídica Assistida",
        "descricao": "Relatório consolidado de testes de segurança",
        "ferramentas_executadas": len(results),
        "resultados": [],
        "resumo": {
            "total": len(results),
            "sucesso": sum(1 for r in results if r.get("success")),
            "falha": sum(1 for r in results if not r.get("success")),
        },
    }

    for result in results:
        entry = {
            "ferramenta": result.get("tool", "desconhecida"),
            "sucesso": result.get("success", False),
            "codigo_retorno": result.get("return_code", -1),
            "caminho_relatorio": result.get("report_path"),
            "erro": result.get("error"),
        }

        # Tenta carregar o relatório individual se existir e for JSON
        report_path = result.get("report_path")
        if report_path and Path(report_path).exists():
            try:
                with open(report_path, encoding="utf-8") as f:
                    entry["detalhes"] = json.load(f)
            except (json.JSONDecodeError, OSError):
                entry["detalhes"] = None

        report["resultados"].append(entry)

    consolidated_path = config.reports_dir / "consolidated_security_report.json"
    with open(consolidated_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return consolidated_path


# ---------------------------------------------------------------------------
# Factory para configuração padrão do projeto
# ---------------------------------------------------------------------------


def get_default_config() -> SecurityTestingConfig:
    """Retorna a configuração padrão de security testing para o projeto.

    Lê variáveis de ambiente para customização:
    - SAFETY_API_KEY: Chave da API Safety
    - ZAP_TARGET_URL: URL alvo para OWASP ZAP
    - ZAP_API_KEY: Chave da API do ZAP
    - ZAP_OPENAPI_URL: URL do OpenAPI spec
    """
    zap_target = os.getenv("ZAP_TARGET_URL", "http://localhost:8000")
    zap_openapi = os.getenv("ZAP_OPENAPI_URL", f"{zap_target}/openapi.json")

    return SecurityTestingConfig(
        bandit=BanditConfig(
            targets=["src/"],
            exclude_dirs=[".venv", "__pycache__", "tests", "migrations", "alembic"],
            skips=["B101"],  # assert em testes
        ),
        safety=SafetyConfig(
            api_key=os.getenv("SAFETY_API_KEY"),
        ),
        pip_audit=PipAuditConfig(
            strict=True,
        ),
        owasp_zap=OwaspZapConfig(
            target_url=zap_target,
            openapi_spec_url=zap_openapi,
            api_key=os.getenv("ZAP_API_KEY"),
            scan_type="api",
            max_duration_minutes=15,
        ),
        fail_on_critical=True,
    )


# ---------------------------------------------------------------------------
# Ponto de entrada para execução direta
# ---------------------------------------------------------------------------


def main() -> int:
    """Ponto de entrada principal para execução via linha de comando.

    Uso:
        python -m src.modules.m12_security_testing_config [comando]

    Comandos:
        run-sast     — Executa Bandit, Safety e pip-audit
        gen-config   — Gera arquivos de configuração
        gen-workflow — Gera workflow do GitHub Actions
        show-config  — Exibe configuração atual
    """
    config = get_default_config()

    command = sys.argv[1] if len(sys.argv) > 1 else "show-config"

    if command == "run-sast":
        print("🔒 Iniciando testes de segurança (SAST + Auditoria de Dependências)...")
        results = run_all_sast(config)
        report_path = generate_consolidated_report(results, config)
        print(f"\n📄 Relatório consolidado gerado em: {report_path}")

        # Retorna código de erro se alguma ferramenta falhou e fail_on_critical está ativo
        if config.fail_on_critical and any(
            not r.get("success") for r in results
        ):
            print("\n⚠️  Algumas verificações de segurança falharam!")
            return 1
        return 0

    elif command == "gen-config":
        print("📝 Gerando arquivos de configuração de security testing...")
        generated = config.generate_all_configs()
        for tool_name, path in generated.items():
            print(f"  ✅ {tool_name}: {path}")
        print("\nArquivos de configuração gerados com sucesso!")
        return 0

    elif command == "gen-workflow":
        print("🔧 Gerando workflow do GitHub Actions...")
        config.ensure_directories()
        workflow_dir = PROJECT_ROOT / ".github" / "workflows"
        workflow_dir.mkdir(parents=True, exist_ok=True)
        workflow_path = workflow_dir / "security-testing.yml"
        workflow_path.write_text(
            config.generate_github_actions_workflow(), encoding="utf-8"
        )
        print(f"  ✅ Workflow gerado em: {workflow_path}")
        return 0

    elif command == "show-config":
        print("🔒 Configuração de Security Testing — Automação Jurídica Assistida")
        print(f"\n📁 Diretório de relatórios: {config.reports_dir}")
        print(f"📁 Diretório de configuração: {config.config_dir}")
        print(f"\n--- Bandit (SAST) ---")
        print(f"  Comando: {' '.join(config.bandit.to_cli_args())}")
        print(f"\n--- Safety (Dependências) ---")
        print(f"  Comando: {' '.join(config.safety.to_cli_args())}")
        print(f"\n--- pip-audit (Dependências) ---")
        print(f"  Comando: {' '.join(config.pip_audit.to_cli_args())}")
        print(f"\n--- OWASP ZAP (DAST) ---")
        print(f"  Comando: {' '.join(config.owasp_zap.to_docker_command())}")
        print(f"\n--- Pipeline CI/CD ---")
        pipeline = config.get_ci_pipeline_config()
        print(json.dumps(pipeline, indent=2, ensure_ascii=False))
        return 0

    else:
        print(f"❌ Comando desconhecido: {command}")
        print("Comandos disponíveis: run-sast, gen-config, gen-workflow, show-config")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
