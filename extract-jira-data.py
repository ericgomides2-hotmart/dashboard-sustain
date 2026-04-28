#!/usr/bin/env python3
"""
Extract Jira ticket data for pending analysis report.
Runs acli commands to get ticket info and last comment.
Outputs JSON for HTML generation.
"""
import subprocess
import json
import sys
import re
from datetime import datetime

TICKETS = """CE-16949 CE-18880 CE-19185 CE-18357 CE-20108 CE-18447 CE-20922 CE-19051 CE-19156 CE-21462
CE-19543 CE-19728 CE-21329 CE-21727 CE-19919 CE-21636 CE-21716 CE-21900 CE-21945 CE-20605
CE-22109 CE-21834 CE-20721 CE-22212 CE-20815 CE-20830 CE-20991 CE-21003 CE-21240 CE-21534
CE-22557 CE-21447 CE-21578 CE-21585 CE-22766 CE-21596 CE-22788 CE-21627 CE-21641 CE-21711
CE-21740 CE-23422 CE-23467 CE-21819 CE-21821 CE-21884 CE-21895 CE-22303 CE-21933 CE-22053
CE-24030 CE-22236 CE-24081 CE-22266 CE-22272 CE-22283 CE-22291 CE-23733 CE-22336 CE-23789
CE-23807 CE-22467 CE-22486 CE-22968 CE-22556 CE-22563 CE-24007 CE-22655 CE-22678 CE-22864
CE-24792 CE-22949 CE-24401 CE-24430 CE-22972 CE-22999 CE-23004 CE-23453 CE-23062 CE-24529
CE-23211 CE-23271 CE-23343 CE-25210 CE-25212 CE-23352 CE-25222 CE-25242 CE-23397 CE-25274
CE-24854 CE-23423 CE-23438 CE-23455 CE-23469 CE-23704 CE-23493 CE-23496 CE-25007 CE-25333
CE-23831 CE-23874 CE-23521 CE-25513 CE-25518 CE-25143 CE-25160 CE-23955 CE-23651 CE-24108
CE-23712 CE-23736 CE-23787 CE-25745 CE-25322 CE-25809 CE-23875 CE-25393 CE-25399 CE-25414
CE-23901 CE-25490 CE-25493 CE-25495 CE-25526 CE-24300 CE-25551 CE-25563 CE-24334 CE-25894
CE-25918 CE-24036 CE-25932 CE-25950 CE-25969 CE-24087 CE-25638 CE-25991 CE-25641 CE-25642
CE-25644 CE-25652 CE-25686 CE-26023 CE-24148 CE-25705 CE-24158 CE-24161 CE-24173 CE-24175
CE-25747 CE-24204 CE-24582 CE-25821 CE-24634 CE-24211 CE-24287 CE-24322 CE-24347 CE-25878
CE-25881 CE-24353 CE-24361 CE-24381 CE-24382 CE-24389 CE-25920 CE-24438 CE-25934 CE-25949
CE-25976 CE-26010 CE-24473 CE-25002 CE-24513 CE-25027 CE-24574 CE-24584 CE-24591 CE-24622
CE-25114 CE-25133 CE-25141 CE-25192 CE-24806 CE-25271 CE-25292 CE-25026 CE-25329 CE-25040
CE-25342 CE-25055 CE-25497 CE-25498 CE-25083 CE-25540 CE-25157 CE-25168 CE-25218 CE-25613
CE-25229 CE-25254 CE-25259 CE-25260 CE-25272 CE-25283 CE-25289 CE-25621 CE-25629 CE-25680
CE-25308 CE-25716 CE-25337 CE-25339 CE-25352 CE-25412 CE-25452 CE-25454 CE-25488 CE-25500
CE-25515 CE-25536 CE-25854 CE-25566 CE-25868 CE-25871 CE-25589 CE-25876 CE-25599 CE-25902
CE-25946 CE-25620 CE-25632 CE-25979 CE-25633 CE-25636 CE-25647 CE-25660 CE-26003 CE-25683
CE-26019 CE-25709 CE-25711 CE-25715 CE-25740 CE-25743 CE-25752 CE-25760 CE-25768 CE-25775
CE-25784 CE-25788 CE-25795 CE-25823 CE-25831 CE-25835 CE-25841 CE-25851 CE-25853 CE-25875
CE-25877 CE-25879 CE-25880 CE-25889 CE-25893 CE-25906 CE-25927 CE-25929 CE-25931 CE-25935
CE-25945 CE-25955 CE-25967 CE-25968 CE-25970 CE-25978 CE-25986 CE-25992 CE-25994 CE-25999
CE-26000 CE-26001 CE-26005 CE-26006 CE-26011 CE-26013 CE-26016 CE-26020""".split()

def get_ticket_data(key):
    try:
        result = subprocess.run(
            ['acli', 'jira', 'workitem', 'view', key, '--json'],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        fields = data.get('fields', {})
        summary = fields.get('summary', '?')
        status = fields.get('status', {}).get('name', '?')
        assignee = fields.get('assignee')
        assignee_name = assignee.get('displayName', '?') if assignee else 'Não atribuído'
        return {
            'key': key,
            'summary': summary,
            'status': status,
            'assignee': assignee_name
        }
    except Exception as e:
        return {'key': key, 'summary': f'Erro: {e}', 'status': '?', 'assignee': '?'}

def get_last_comment(key):
    try:
        result = subprocess.run(
            ['acli', 'jira', 'workitem', 'comment', 'list', '--key', key, '--json'],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return None, None
        data = json.loads(result.stdout)
        comments = data.get('comments', [])
        if not comments:
            return 'Sem comentários', None
        last = comments[-1]
        author = last.get('author', '?')
        body = last.get('body', '')[:200]
        return author, body
    except:
        return '?', '?'

def categorize(summary):
    s = summary.lower()
    if any(w in s for w in ['assinatura', 'subscription', 'recorrência', 'recorrencia', 'renovação', 'renovacao', 'cancelamento assinatura', 'congelamento', 'descongelamento', 'troca de plano', 'switch plan']):
        return 'Assinaturas'
    if any(w in s for w in ['checkout', 'pagamento', 'parcelamento', 'boleto', 'pix', 'cartão', 'cartao', 'cobrança', 'cobranca', 'valor incorreto', 'cupom', 'juros']):
        return 'Checkout / Pagamento'
    if any(w in s for w in ['nota fiscal', 'nfs', 'enotas', 'fiscal', 'csrt']):
        return 'Fiscal / eNotas'
    if any(w in s for w in ['webhook', 'postback', 'integração', 'integracao', 'quaderno']):
        return 'Webhook / Integração'
    if any(w in s for w in ['e-mail', 'email', 'notificação', 'notificacao']):
        return 'Emails / Notificações'
    if any(w in s for w in ['acesso', 'club', 'ingresso', 'eticket', 'checkin']):
        return 'Acesso / E-ticket'
    if any(w in s for w in ['autofix', 'massa', 'bulk']):
        return 'Operações em Massa'
    if any(w in s for w in ['vulcano', 'funil', 'oferta', 'produto', 'colaborador']):
        return 'Vulcano / Produto'
    if any(w in s for w in ['saque', 'withdraw', 'financeiro', 'comissão', 'comissao']):
        return 'Financeiro / Comissão'
    if any(w in s for w in ['agente', 'vendas ia']):
        return 'Agente de Vendas'
    if any(w in s for w in ['sepa', 'gateway', 'adyen']):
        return 'Gateway / Métodos'
    return 'Outros'

def determine_pending(last_author, status, assignee):
    if last_author and 'Sustain' in str(last_author):
        return 'Sustain (aguardando análise)', 'red'
    if last_author and any(w in str(last_author).lower() for w in ['automation', 'bot']):
        return 'Automação (sem ação humana)', 'orange'
    if status in ('Aberto', 'Open'):
        return 'Não iniciado', 'red'
    if status in ('Under Analysis',):
        return f'Em análise ({assignee})', 'blue'
    if status in ('Reaberto',):
        return f'Reaberto ({assignee})', 'orange'
    return f'Último: {last_author}', 'gray'

if __name__ == '__main__':
    results = []
    total = len(TICKETS)
    for i, key in enumerate(TICKETS):
        print(f'[{i+1}/{total}] {key}...', file=sys.stderr)
        ticket = get_ticket_data(key)
        if not ticket:
            continue
        last_author, last_body = get_last_comment(key)
        ticket['last_comment_author'] = str(last_author) if last_author else '?'
        ticket['last_comment_snippet'] = str(last_body)[:150] if last_body else ''
        ticket['category'] = categorize(ticket['summary'])
        pending, color = determine_pending(last_author, ticket['status'], ticket['assignee'])
        ticket['pending'] = pending
        ticket['pending_color'] = color
        results.append(ticket)

    with open('tickets-pending-analysis.json', 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f'\nDone: {len(results)} tickets processed', file=sys.stderr)
