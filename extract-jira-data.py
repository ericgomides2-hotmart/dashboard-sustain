#!/usr/bin/env python3
"""
Extrator de dados JIRA para o Dashboard CX.
Gera o arquivo data.js consumido pelo index.html.
"""
import json, os, sys
from datetime import datetime

try:
    import requests
except ImportError:
    print("ERRO: pip install requests")
    sys.exit(1)

JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL", "https://hotmart.atlassian.net")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "")
JIRA_TOKEN = os.environ.get("JIRA_TOKEN", "")

CF_CAMADA_SERVICO = "customfield_14189"
CF_PRODUTO_FRENTE = "customfield_25966"
CF_PRIORITY_CX = "customfield_14464"
CF_SEGMENTACAO_CX = "customfield_26064"
CF_PARTNER = "customfield_11854"
CF_JIRA_PROJECT_KEY = "customfield_25542"
CF_JIRA_PROJECT = "customfield_14589"

JQL = (
    '(project = bic AND issuetype = Support AND created >= "2024-08-01") '
    'OR (project = CE AND "Camada de Serviço[Select List (cascading)]" IN ('
    '"Hotpay: Pagamento, valores aplicados no pós venda, comissão creator", '
    '"Cartão Hotmart", '
    '"Assinatura: Configuração planos de assinatura, cupons, troca de plano, '
    'período trial, cancelamento de assinaturas e qualquer outra ferramenta '
    'sobre definir e rodar uma estratégia de vendas recorrentes", '
    '"Wallet:Antecipação, solicitação de saque, extrato", '
    'Bundle, "WhatsApp e Chat da Plataforma", "Commercial Agent", '
    'Antecipação, Saque, KYC, Selfbilling, '
    '"Validação cadastro de creator", Extrato, Saldo, Holding, '
    '"Renovação antecipada", "Order Bump", "Funil de vendas", '
    '"Abandono de carrinho", Builder, "Thanks page", "Fast buy", '
    '"Métodos de pagamento", "Cupom de desconto", "Interface do checkout", '
    'HUB, "Troca de cartão", "Troca de Plano de assinaturas", '
    '"Cadastro de Creators", "Cálculo de Comissão", '
    '"Recuperador automático de recorrências", "Cancelamento de assinaturas", '
    '"Congelamento e Descongelamento de assinaturas", '
    '"Negociação de parcelas", "Smart Installment", '
    '"Aprovação de compras", "Reembolso de compras", '
    '"Criação de compra", "Remoção de cartão da conta do cliente", '
    '"Status de compra", "e-Notas", Send, Pages) '
    'AND status NOT IN (canceled, cancelled, cancelado) '
    'AND created >= "2024-08-01" '
    'AND labels NOT IN (OrderCheckerMaintenance)) '
    'ORDER BY id DESC'
)

FIELDS = ",".join([
    "key", "summary", "status", "priority", "created", "resolutiondate", "labels",
    "assignee",
    CF_CAMADA_SERVICO, CF_PRODUTO_FRENTE, CF_PRIORITY_CX,
    CF_SEGMENTACAO_CX, CF_PARTNER, CF_JIRA_PROJECT_KEY, CF_JIRA_PROJECT
])

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.js")


def extract_partner(val):
    if val is None: return ""
    if isinstance(val, list):
        return ", ".join(p.get("value", p.get("name", "")) for p in val if isinstance(p, dict))
    if isinstance(val, dict): return val.get("value", val.get("name", ""))
    return str(val)

def fetch_all_issues():
    if not JIRA_EMAIL or not JIRA_TOKEN:
        print("ERRO: Configure JIRA_EMAIL e JIRA_TOKEN como variáveis de ambiente.")
        sys.exit(1)
    auth = (JIRA_EMAIL, JIRA_TOKEN)
    headers = {"Accept": "application/json"}
    all_tickets = []
    next_page_token = None
    page = 0
    while True:
        url = f"{JIRA_BASE_URL}/rest/api/3/search/jql"
        params = {"jql": JQL, "fields": FIELDS, "maxResults": 100}
        if next_page_token: params["nextPageToken"] = next_page_token
        page += 1
        print(f"  Página {page}...")
        resp = requests.get(url, params=params, auth=auth, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        for issue in data.get("issues", []):
            f = issue.get("fields", {})
            cs = f.get(CF_CAMADA_SERVICO)
            jp = f.get(CF_JIRA_PROJECT)
            camadaPai = ""
            camadaFilho = ""
            if cs and isinstance(cs, dict):
                camadaPai = cs.get("value", "")
                if cs.get("child") and isinstance(cs["child"], dict):
                    camadaFilho = cs["child"].get("value", "")
            ticket = {
                "key": issue.get("key", ""),
                "summary": (f.get("summary", "") or "")[:120],
                "status": (f.get("status") or {}).get("name", ""),
                "priority": (f.get("priority") or {}).get("name", ""),
                "created": f.get("created", ""),
                "resolutiondate": f.get("resolutiondate"),
                "labels": f.get("labels", []),
                "assignee": (f.get("assignee") or {}).get("displayName", "") if isinstance(f.get("assignee"), dict) else "",
                "produtoFrente": f.get(CF_PRODUTO_FRENTE, "") or "",
                "camadaServico": camadaPai,
                "camadaServicoFilho": camadaFilho,
                "priorityCX": (f.get(CF_PRIORITY_CX) or {}).get("value", "") if isinstance(f.get(CF_PRIORITY_CX), dict) else "",
                "segmentacao": (f.get(CF_SEGMENTACAO_CX) or {}).get("value", "") if isinstance(f.get(CF_SEGMENTACAO_CX), dict) else "",
                "partner": extract_partner(f.get(CF_PARTNER)),
                "jiraProjectKey": f.get(CF_JIRA_PROJECT_KEY, "") or "",
                "jiraProjectName": jp.get("name", "") if isinstance(jp, dict) else ""
            }
            all_tickets.append(ticket)
        if data.get("isLast", True) or not data.get("nextPageToken"): break
        next_page_token = data["nextPageToken"]
    print(f"  Total: {len(all_tickets)} tickets.")
    return all_tickets

def main():
    print("Dashboard CX — Extrator JIRA")
    print(f"  JIRA: {JIRA_BASE_URL}")
    tickets = fetch_all_issues()
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    content = f'var JIRA_DATA_DATE = "{now}";\n'
    content += f"// Total: {len(tickets)} tickets\n"
    content += "var JIRA_DATA = "
    content += json.dumps(tickets, ensure_ascii=False, separators=(",", ":"))
    content += ";\n"
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Arquivo: {OUTPUT_FILE}")
    print("Pronto!")

if __name__ == "__main__":
    main()
