"""Create screenshot-ready panels from the saved, verified AWS responses."""
import argparse
from html import escape
import json
from pathlib import Path
from verify_traces import tool_results

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--directory', type=Path, default=ROOT / 'examples/cloud_final')
directory = parser.parse_args().directory.resolve()

def load(name):
    return json.loads((directory / (name + '.json')).read_text(encoding='utf-8'))

style = '''body{margin:0;background:#edf1f5;color:#17283c;font:16px Arial,sans-serif}
main{box-sizing:border-box;width:1100px;margin:24px auto;padding:30px;background:white;border:1px solid #d2dbe4;border-radius:12px}
h1{font-size:27px;margin:0 0 12px}h2{font-size:19px;margin:22px 0 10px}
.meta,.foot{color:#52687c;font-size:13px;line-height:1.6;overflow-wrap:anywhere}
.badge{background:#e6f3ea;color:#14643e;font-weight:bold;padding:12px 15px;margin:18px 0}
.box,pre{background:#f6f8fa;border-left:4px solid #278158;padding:16px;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.55}
pre{font:14px Consolas,monospace;line-height:1.55}table{border-collapse:collapse;width:100%}
td,th{padding:12px;text-align:left;border-bottom:1px solid #dfe5eb}th{background:#f0f3f7}
.pass{color:#14643e;font-weight:bold}'''

def page(name, title, body):
    html = '<!doctype html><html lang="en"><meta charset="utf-8"><title>' + escape(title) + '</title><style>' + style + '</style><main id="outcome">' + body + '</main></html>'
    (directory / (name + '.html')).write_text(html, encoding='utf-8')

report=load('verification')
assert report['submission_ready'], 'Do not render successful panels before evidence verification passes'
titles={'order':'Order tracking','refund':'API and Lambda refund','rag':'Knowledge Base RAG','memory_a':'Memory — session A','memory_b':'Memory — session B','discount':'Code Interpreter discount','browser':'Live browser navigation'}
rows=[]
for key,title in titles.items():
    record=load(key)
    meta=escape(record['runtime_arn'])+'<br>'+escape(record['completed_utc'])+' | us-east-1 | HTTP '+str(record['http_status'])+' | runtime version '+escape(record['runtime_version'])
    response=record['output']['response']
    body='<h1>'+escape(title)+'</h1><div class="meta">'+meta+'</div><div class="badge">VERIFIED AWS RESPONSE</div><h2>Request</h2><div class="box">'+escape(record['input']['prompt'])+'</div><h2>Agent response</h2><pre>'+escape(response)+'</pre>'
    if key=='rag':
        excerpts=[]
        for name,result in tool_results(record):
            if name=='search_knowledge_base':
                for block in result.get('content',[]):
                    excerpts.extend(line for line in block.get('text','').splitlines() if 'platinum' in line.lower())
        body+='<h2>Retrieved catalog excerpt</h2><pre>'+escape('\n'.join(dict.fromkeys(excerpts)))+'</pre>'
    if key in ('memory_a','memory_b'):
        body+='<div class="meta">Customer: '+escape(record['input']['customer_id'])+'<br>Runtime session: '+escape(record['runtime_session_id'])+'</div>'
    body+='<p class="foot">Source: '+escape(key+'.json')+' — saved output of the actual deployed AgentCore Runtime invocation. This panel displays recorded results; it is not the AWS console.</p>'
    page(key+'_outcome',title,body)
    if key!='memory_a': rows.append('<tr><td>'+escape(title)+'</td><td class="pass">PASS</td><td>'+escape(response)+'</td></tr>')

body='<h1>Complete AWS deployment outcomes</h1><div class="meta">'+escape(report['runtime_arn'])+'<br>September 18, 2026 (India) | Authorized personal AWS test account | us-east-1</div><div class="badge">6 of 6 required live scenarios passed | Both reviewer corrections verified</div><table><tr><th>Scenario</th><th>Result</th><th>Actual response</th></tr>'+''.join(rows)+'</table><p class="foot">Saved actual AWS responses in examples/cloud_final. All six scenarios and the CLI check used the same runtime and current main.py. Separate runtime versions were used for deliberate empty-KB and dummy-Gateway tests. Personal AWS was authorized after the sandbox denied vector-store permissions. Udacity acceptance remains pending.</p>'
page('outcomes','Complete AWS deployment outcomes',body)
print('Created',len(titles)+1,'panels from verified responses.')
