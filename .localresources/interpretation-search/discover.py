"""Bounded public metadata discovery through the local ResearchAssistant API."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import sys

sys.path.insert(0, '/home/chakwong/python/ResearchAssistant/src')
from research_assistant.query.discovery import discover_papers_with_status

QUERIES = {
    'statutory-argumentation': 'An argumentation framework for contested cases of statutory interpretation',
    'legal-theories-values': 'A model of legal reasoning with cases incorporating theories and values',
    'carneades': 'The Carneades model of argument and burden of proof',
    'interpretation-abduction': 'legal interpretation abduction argumentation',
    'truth-maintenance': 'An assumption-based TMS de Kleer',
    'hypo': 'HYPO A precedent-based legal reasoner',
    'active-learning': 'The geometry of generalized binary search',
    'tree-of-thoughts': 'Tree of Thoughts Deliberate Problem Solving with Large Language Models',
}

def fetch(item):
    key, query = item
    payload = discover_papers_with_status(query, per_page=3)
    path = Path(__file__).parent / f'{key}-discovery.json'
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    return key, payload.get('status'), len(payload.get('results', []))

if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = [pool.submit(fetch, item) for item in QUERIES.items()]
        for job in as_completed(jobs):
            print(json.dumps(job.result()), flush=True)
