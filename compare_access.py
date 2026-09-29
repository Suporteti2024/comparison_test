"""
Teste de comparação: WebService SOAP (legado) x API REST (nova versão)
Validação de acesso - Hebraica

Regra principal (bloqueante):
    SOAP <AccessResult>  x  REST "allowed"
        Allow  <-> true
        Deny   <-> false

Regras secundárias (divergência de dados, não reprovam o caso, mas são reportadas):
    Code       <-> barcode
    CodeID     <-> CodeID
    CodeType   <-> CodeType
    AccessMode <-> accessMode

Uso:
    python compare_access.py --gerar-modelo entrada.xlsx
    python compare_access.py entrada.xlsx
    python compare_access.py entrada.xlsx -o resultado.xlsx --workers 4 --timeout 15
"""

import argparse
import json
import sys
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, asdict
from datetime import datetime
from xml.sax.saxutils import escape

import requests
import urllib3
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

# --------------------------------------------------------------------------- #
# Configuração
# --------------------------------------------------------------------------- #
SOAP_URL = "https://appmc.hebraica.org.br:9133/MultiClubes.OnlineServices/Services/Extensions/Access/v1.svc"
SOAP_ACTION = '"http://multiclubes.com.br/access/v1/IService/Validate"'
REST_URL = "https://validate.hebraica.org.br/v1/access/validate"

NS = {
    "s": "http://schemas.xmlsoap.org/soap/envelope/",
    "v1": "http://multiclubes.com.br/access/v1",
    "a": "http://schemas.datacontract.org/2004/07/MultiClubes.OnlineServices.Services.Extensions.Access.v1",
    "i": "http://www.w3.org/2001/XMLSchema-instance",
}

SOAP_TEMPLATE = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:v1="http://multiclubes.com.br/access/v1" xmlns:mul="http://schemas.datacontract.org/2004/07/MultiClubes.OnlineServices.Services.Extensions.Access.v1">
   <soapenv:Header/>
   <soapenv:Body>
      <v1:Validate>
         <v1:data>
            <mul:AccessCode>{code}</mul:AccessCode>
            <mul:AccessMode>{mode}</mul:AccessMode>
            <mul:Device>{device}</mul:Device>
         </v1:data>
      </v1:Validate>
   </soapenv:Body>
</soapenv:Envelope>"""

# Mapeamento AccessResult (SOAP) -> booleano equivalente ao "allowed" (REST)
ACCESS_RESULT_MAP = {"allow": True, "allowed": True, "grant": True, "granted": True,
                     "deny": False, "denied": False}

INPUT_COLUMNS = ["AccessCode", "AccessMode", "Device"]
VALID_MODES = {"Entrance", "Exit"}

STATUS_OK = "OK"
STATUS_OK_DIV = "OK COM DIVERGÊNCIA"
STATUS_FAIL = "FALHA"
STATUS_ERROR = "ERRO"


# --------------------------------------------------------------------------- #
# Modelos
# --------------------------------------------------------------------------- #
@dataclass
class TestCase:
    row: int
    access_code: str
    access_mode: str
    device: str
    expected: str = ""  # opcional: "Allow"/"Deny" esperado informado na planilha


@dataclass
class SoapResult:
    ok: bool = False
    http_status: int | None = None
    time_ms: int | None = None
    access_result: str | None = None
    allowed: bool | None = None
    access_mode: str | None = None
    code: str | None = None
    code_id: str | None = None
    code_type: str | None = None
    message: str | None = None
    error: str | None = None
    raw: str = ""


@dataclass
class RestResult:
    ok: bool = False
    http_status: int | None = None
    time_ms: int | None = None
    allowed: bool | None = None
    barcode: str | None = None
    access_mode: str | None = None
    code_id: str | None = None
    code_type: str | None = None
    person_type: str | None = None
    person_name: str | None = None
    block_reason: str | None = None
    register_type: str | None = None
    message: str | None = None
    error: str | None = None
    raw: str = ""


@dataclass
class Comparison:
    case: TestCase
    soap: SoapResult
    rest: RestResult
    status: str = ""
    allowed_match: bool | None = None
    divergences: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Chamadas
# --------------------------------------------------------------------------- #
def _text(el, path):
    node = el.find(path, NS)
    if node is None or node.get(f"{{{NS['i']}}}nil") == "true":
        return None
    return (node.text or "").strip()


def call_soap(session: requests.Session, case: TestCase, timeout: float) -> SoapResult:
    r = SoapResult()
    body = SOAP_TEMPLATE.format(code=escape(case.access_code),
                                mode=escape(case.access_mode),
                                device=escape(case.device))
    headers = {"Content-Type": "text/xml;charset=UTF-8", "SOAPAction": SOAP_ACTION}
    start = time.perf_counter()
    try:
        resp = session.post(SOAP_URL, data=body.encode("utf-8"), headers=headers, timeout=timeout)
        r.time_ms = int((time.perf_counter() - start) * 1000)
        r.http_status = resp.status_code
        r.raw = resp.text

        root = ET.fromstring(resp.content)
        fault = root.find(".//s:Fault", NS)
        if fault is not None:
            r.error = f"SOAP Fault: {(fault.findtext('faultstring') or '').strip()}"
            return r

        res = root.find(".//v1:ValidateResult", NS)
        if res is None:
            r.error = f"ValidateResult ausente (HTTP {resp.status_code})"
            return r

        r.access_result = _text(res, "a:AccessResult")
        r.access_mode = _text(res, "a:AccessMode")
        r.code = _text(res, "a:Code")
        r.code_id = _text(res, "a:CodeID")
        r.code_type = _text(res, "a:CodeType")
        r.message = _text(res, "a:Message")
        r.allowed = ACCESS_RESULT_MAP.get((r.access_result or "").lower())
        if r.allowed is None:
            r.error = f"AccessResult desconhecido: {r.access_result!r}"
            return r
        r.ok = True
    except requests.RequestException as e:
        r.time_ms = int((time.perf_counter() - start) * 1000)
        r.error = f"Erro de conexão: {type(e).__name__}: {e}"
    except ET.ParseError as e:
        r.error = f"XML inválido: {e}"
    return r


def call_rest(session: requests.Session, case: TestCase, timeout: float) -> RestResult:
    r = RestResult()
    payload = {"AccessCode": case.access_code, "AccessMode": case.access_mode, "Device": case.device}
    start = time.perf_counter()
    try:
        resp = session.post(REST_URL, json=payload, headers={"Content-Type": "application/json"},
                            timeout=timeout)
        r.time_ms = int((time.perf_counter() - start) * 1000)
        r.http_status = resp.status_code
        r.raw = resp.text

        data = resp.json()
        if not isinstance(data, dict):
            r.error = f"Resposta não é objeto JSON (HTTP {resp.status_code})"
            return r
        if "allowed" not in data:
            r.error = f"Campo 'allowed' ausente (HTTP {resp.status_code})"
            return r
        if not isinstance(data["allowed"], bool):
            r.error = f"Campo 'allowed' não é booleano: {data['allowed']!r}"
            return r

        r.allowed = data["allowed"]
        r.barcode = _str(data.get("barcode"))
        r.access_mode = _str(data.get("accessMode"))
        r.code_id = _str(data.get("CodeID"))
        r.code_type = _str(data.get("CodeType"))
        r.person_type = _str(data.get("personType"))
        r.person_name = _str(data.get("personName"))
        r.block_reason = _str(data.get("blockReason"))
        r.register_type = _str(data.get("RegisterType"))
        r.message = _str(data.get("message"))
        r.ok = True
    except requests.RequestException as e:
        r.time_ms = int((time.perf_counter() - start) * 1000)
        r.error = f"Erro de conexão: {type(e).__name__}: {e}"
    except ValueError as e:
        r.error = f"JSON inválido (HTTP {r.http_status}): {e}"
    return r


def _str(v):
    return None if v is None else str(v).strip()


# --------------------------------------------------------------------------- #
# Comparação
# --------------------------------------------------------------------------- #
def compare(case: TestCase, soap: SoapResult, rest: RestResult) -> Comparison:
    c = Comparison(case=case, soap=soap, rest=rest)

    if not soap.ok or not rest.ok:
        c.status = STATUS_ERROR
        if not soap.ok:
            c.notes.append(f"SOAP: {soap.error}")
        if not rest.ok:
            c.notes.append(f"REST: {rest.error}")
        return c

    # Regra principal
    c.allowed_match = soap.allowed == rest.allowed
    if not c.allowed_match:
        c.divergences.append(
            f"DECISÃO: SOAP={soap.access_result} x REST allowed={str(rest.allowed).lower()}")

    # Regras secundárias
    pairs = [
        ("Code/barcode", soap.code, rest.barcode),
        ("CodeID", soap.code_id, rest.code_id),
        ("CodeType", soap.code_type, rest.code_type),
        ("AccessMode", soap.access_mode, rest.access_mode),
    ]
    for name, s, r in pairs:
        if (s or "").lower() != (r or "").lower():
            c.divergences.append(f"{name}: SOAP={s!r} x REST={r!r}")

    # Resultado esperado informado na planilha (opcional)
    if case.expected:
        exp = ACCESS_RESULT_MAP.get(case.expected.strip().lower())
        if exp is None:
            c.notes.append(f"Valor esperado inválido: {case.expected!r}")
        elif exp != rest.allowed:
            c.allowed_match = False
            c.divergences.append(f"ESPERADO={case.expected} x REST allowed={str(rest.allowed).lower()}")

    if rest.http_status and rest.http_status >= 400:
        c.notes.append(f"REST retornou HTTP {rest.http_status}")

    if c.allowed_match is False:
        c.status = STATUS_FAIL
    elif c.divergences:
        c.status = STATUS_OK_DIV
    else:
        c.status = STATUS_OK
    return c


# --------------------------------------------------------------------------- #
# Excel - entrada
# --------------------------------------------------------------------------- #
def create_template(path: str):
    wb = Workbook()
    ws = wb.active
    ws.title = "Casos"
    headers = INPUT_COLUMNS + ["ResultadoEsperado", "Observacao"]
    ws.append(headers)
    ws.append(["20314676", "Entrance", "HungriaEntrada1", "Deny", "Visitante com autorização expirada"])
    ws.append(["20314676", "Exit", "HungriaSaida1", "", "Mesmo código na saída"])
    for i, h in enumerate(headers, 1):
        ws.cell(row=1, column=i).font = Font(bold=True, color="FFFFFF")
        ws.cell(row=1, column=i).fill = PatternFill("solid", fgColor="1F4E78")
        ws.column_dimensions[get_column_letter(i)].width = 22
    # AccessCode como texto para não perder zeros à esquerda
    for row in ws.iter_rows(min_row=2, max_col=1):
        for cell in row:
            cell.number_format = "@"
    wb.save(path)
    print(f"Modelo criado: {path}")


def read_cases(path: str) -> list[TestCase]:
    wb = load_workbook(path, data_only=True, read_only=True)
    ws = wb.active
    rows = ws.iter_rows(values_only=True)
    header = [str(h).strip() if h is not None else "" for h in next(rows)]
    idx = {h.lower(): i for i, h in enumerate(header)}

    missing = [c for c in INPUT_COLUMNS if c.lower() not in idx]
    if missing:
        sys.exit(f"Colunas obrigatórias ausentes na planilha: {missing}. Encontradas: {header}")

    def get(row, col):
        i = idx.get(col.lower())
        if i is None or i >= len(row) or row[i] is None:
            return ""
        v = row[i]
        if isinstance(v, float) and v.is_integer():
            v = int(v)
        return str(v).strip()

    cases = []
    for n, row in enumerate(rows, start=2):
        code, mode, device = get(row, "AccessCode"), get(row, "AccessMode"), get(row, "Device")
        if not (code or mode or device):
            continue
        if mode and mode not in VALID_MODES:
            print(f"  [aviso] linha {n}: AccessMode {mode!r} fora de {sorted(VALID_MODES)}")
        cases.append(TestCase(row=n, access_code=code, access_mode=mode, device=device,
                              expected=get(row, "ResultadoEsperado")))
    wb.close()
    return cases


# --------------------------------------------------------------------------- #
# Excel - relatório
# --------------------------------------------------------------------------- #
FILLS = {
    STATUS_OK: PatternFill("solid", fgColor="C6EFCE"),
    STATUS_OK_DIV: PatternFill("solid", fgColor="FFEB9C"),
    STATUS_FAIL: PatternFill("solid", fgColor="FFC7CE"),
    STATUS_ERROR: PatternFill("solid", fgColor="D9D9D9"),
}
HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(bold=True, color="FFFFFF")


def _header(ws, headers, widths=None):
    ws.append(headers)
    for i, _ in enumerate(headers, 1):
        cell = ws.cell(row=1, column=i)
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = (widths or {}).get(i, 18)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def _b(v):
    return "" if v is None else str(v).lower()


def write_report(path: str, results: list[Comparison], started: datetime, finished: datetime):
    wb = Workbook()

    # ---- Resumo
    ws = wb.active
    ws.title = "Resumo"
    total = len(results)
    count = {s: sum(1 for r in results if r.status == s) for s in FILLS}
    comparable = total - count[STATUS_ERROR]
    compat = count[STATUS_OK] + count[STATUS_OK_DIV]
    soap_t = [r.soap.time_ms for r in results if r.soap.time_ms is not None]
    rest_t = [r.rest.time_ms for r in results if r.rest.time_ms is not None]

    rows = [
        ("Teste de comparação SOAP x REST - Validação de acesso", ""),
        ("", ""),
        ("Início", started.strftime("%d/%m/%Y %H:%M:%S")),
        ("Fim", finished.strftime("%d/%m/%Y %H:%M:%S")),
        ("SOAP", SOAP_URL),
        ("REST", REST_URL),
        ("", ""),
        ("Total de casos", total),
        (STATUS_OK, count[STATUS_OK]),
        (STATUS_OK_DIV, count[STATUS_OK_DIV]),
        (STATUS_FAIL, count[STATUS_FAIL]),
        (STATUS_ERROR, count[STATUS_ERROR]),
        ("Compatibilidade da decisão (allowed x AccessResult)",
         f"{compat / comparable:.1%}" if comparable else "n/a"),
        ("", ""),
        ("Tempo médio SOAP (ms)", round(sum(soap_t) / len(soap_t)) if soap_t else "n/a"),
        ("Tempo médio REST (ms)", round(sum(rest_t) / len(rest_t)) if rest_t else "n/a"),
        ("Tempo máximo SOAP (ms)", max(soap_t) if soap_t else "n/a"),
        ("Tempo máximo REST (ms)", max(rest_t) if rest_t else "n/a"),
        ("", ""),
        ("VEREDITO", "APROVADO" if total and count[STATUS_FAIL] == 0 and count[STATUS_ERROR] == 0
         else "REPROVADO"),
    ]
    for r in rows:
        ws.append(r)
    ws["A1"].font = Font(bold=True, size=14)
    for i, s in enumerate([STATUS_OK, STATUS_OK_DIV, STATUS_FAIL, STATUS_ERROR], start=9):
        ws.cell(row=i, column=1).fill = FILLS[s]
    verdict = ws.cell(row=len(rows), column=2)
    verdict.font = Font(bold=True, size=12)
    verdict.fill = FILLS[STATUS_OK] if verdict.value == "APROVADO" else FILLS[STATUS_FAIL]
    ws.column_dimensions["A"].width = 52
    ws.column_dimensions["B"].width = 90

    # ---- Resultados
    ws = wb.create_sheet("Resultados")
    headers = [
        "Linha", "AccessCode", "AccessMode", "Device", "Esperado", "STATUS",
        "SOAP AccessResult", "REST allowed", "Decisão compatível",
        "SOAP HTTP", "REST HTTP", "SOAP ms", "REST ms",
        "SOAP Code", "REST barcode", "SOAP CodeID", "REST CodeID",
        "SOAP CodeType", "REST CodeType", "SOAP AccessMode", "REST accessMode",
        "SOAP Message", "REST message", "REST personType", "REST personName",
        "REST blockReason", "REST RegisterType", "Divergências", "Observações",
    ]
    _header(ws, headers, {1: 7, 6: 20, 22: 40, 23: 40, 25: 30, 28: 60, 29: 60})
    status_col = headers.index("STATUS") + 1
    for c in results:
        s, r = c.soap, c.rest
        ws.append([
            c.case.row, c.case.access_code, c.case.access_mode, c.case.device, c.case.expected,
            c.status, s.access_result, _b(r.allowed),
            "" if c.allowed_match is None else ("SIM" if c.allowed_match else "NÃO"),
            s.http_status, r.http_status, s.time_ms, r.time_ms,
            s.code, r.barcode, s.code_id, r.code_id,
            s.code_type, r.code_type, s.access_mode, r.access_mode,
            s.message, r.message, r.person_type, r.person_name,
            r.block_reason, r.register_type,
            "\n".join(c.divergences), "\n".join(c.notes),
        ])
        ws.cell(row=ws.max_row, column=status_col).fill = FILLS[c.status]
        ws.cell(row=ws.max_row, column=2).number_format = "@"
    ws.auto_filter.ref = ws.dimensions

    # ---- Falhas (somente o que precisa de atenção)
    ws = wb.create_sheet("Falhas")
    _header(ws, ["Linha", "AccessCode", "AccessMode", "Device", "STATUS", "Detalhe"],
            {1: 7, 6: 100})
    for c in results:
        if c.status in (STATUS_FAIL, STATUS_ERROR):
            ws.append([c.case.row, c.case.access_code, c.case.access_mode, c.case.device,
                       c.status, "\n".join(c.divergences + c.notes)])
            ws.cell(row=ws.max_row, column=5).fill = FILLS[c.status]

    # ---- Evidências (respostas brutas)
    ws = wb.create_sheet("Evidencias")
    _header(ws, ["Linha", "AccessCode", "SOAP (XML)", "REST (JSON)"], {1: 7, 3: 90, 4: 90})
    for c in results:
        rest_raw = c.rest.raw
        try:
            rest_raw = json.dumps(json.loads(rest_raw), ensure_ascii=False, indent=2)
        except (ValueError, TypeError):
            pass
        ws.append([c.case.row, c.case.access_code, c.soap.raw[:32000], rest_raw[:32000]])

    wb.save(path)


# --------------------------------------------------------------------------- #
# Execução
# --------------------------------------------------------------------------- #
def run_case(case: TestCase, timeout: float, verify: bool) -> Comparison:
    with requests.Session() as session:
        session.verify = verify
        soap = call_soap(session, case, timeout)
        rest = call_rest(session, case, timeout)
    return compare(case, soap, rest)


def main():
    p = argparse.ArgumentParser(description="Comparação SOAP x REST - validação de acesso")
    p.add_argument("entrada", nargs="?", help="Planilha .xlsx com AccessCode, AccessMode, Device")
    p.add_argument("-o", "--saida", help="Planilha de resultado (padrão: resultado_<data>.xlsx)")
    p.add_argument("--gerar-modelo", metavar="ARQUIVO", help="Gera uma planilha modelo e sai")
    p.add_argument("--workers", type=int, default=1, help="Casos em paralelo (padrão 1)")
    p.add_argument("--timeout", type=float, default=15, help="Timeout por requisição em s")
    p.add_argument("--insecure", action="store_true", help="Não validar certificado SSL")
    args = p.parse_args()

    if args.gerar_modelo:
        create_template(args.gerar_modelo)
        return
    if not args.entrada:
        p.error("informe a planilha de entrada ou use --gerar-modelo")

    if args.insecure:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    cases = read_cases(args.entrada)
    if not cases:
        sys.exit("Nenhum caso encontrado na planilha.")
    print(f"{len(cases)} caso(s) carregado(s) de {args.entrada}")

    started = datetime.now()
    results: list[Comparison] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futures = [ex.submit(run_case, c, args.timeout, not args.insecure) for c in cases]
        for i, f in enumerate(futures, 1):
            c = f.result()
            results.append(c)
            print(f"[{i}/{len(cases)}] {c.case.access_code:<12} {c.case.access_mode:<9} "
                  f"{c.case.device:<20} SOAP={c.soap.access_result or '-':<6} "
                  f"REST={_b(c.rest.allowed) or '-':<6} -> {c.status}")
    finished = datetime.now()

    out = args.saida or f"resultado_{started:%Y%m%d_%H%M%S}.xlsx"
    write_report(out, results, started, finished)

    fails = sum(1 for r in results if r.status in (STATUS_FAIL, STATUS_ERROR))
    print(f"\nRelatório: {out}")
    print(f"OK: {sum(r.status == STATUS_OK for r in results)} | "
          f"OK c/ divergência: {sum(r.status == STATUS_OK_DIV for r in results)} | "
          f"FALHA: {sum(r.status == STATUS_FAIL for r in results)} | "
          f"ERRO: {sum(r.status == STATUS_ERROR for r in results)}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
