#!/usr/bin/env python3
"""Run Lab 3 Parts 7 and 8 inside the supplied Linux VM (Python 3 stdlib only).

Run from the repository root: python3 lab3_parts7_8.py
Prepare without running:      python3 lab3_parts7_8.py --prepare-only
Resume a stopped batch:       python3 lab3_parts7_8.py --resume RUN_ID
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime
import uuid
import xml.etree.ElementTree as ET

VERSION = 1
RUNNER_REVISION = '3 (checked against repository logs)'
TOOLS = Path('tools/x86_trace_generator')
BASE_CONFIG = 'lab3_1_8KB_64B_1_RANDOM_16KB_64_2_LRU.xml'
BASE_BM = 'cache_test_4KB_4_1.c'
ASSOC_BM = 'cache_test_2Arrays_4KB_4_1.c'
TAIL = ['num_requests', 'num_hits', 'num_misses', 'hit_rate', 'execution_time']


def say(message):
    print(message, flush=True)


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='\n') as stream:
        stream.write(text)


def write_input(path, text):
    """Never replace an input that somebody changed between runs."""
    if path.exists() and path.read_text(encoding='utf-8') != text:
        raise RuntimeError('Generated input was edited; start a new batch: ' + str(path))
    write_text(path, text)


def write_csv(path, label, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.csv.tmp')
    with temp.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow([label] + TAIL)
        writer.writerows(rows)
    temp.replace(path)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def change_define(source, name, value):
    source, count = re.subn(r'^\s*#define\s+' + name + r'\s+[^\n]+',
                            '#define ' + name + ' ' + value, source,
                            flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError('Expected one #define ' + name)
    return source


def read_inputs(repo):
    paths = [repo / TOOLS / 'LAB3_BMs' / BASE_BM,
             repo / TOOLS / 'LAB3_BMs' / ASSOC_BM,
             repo / TOOLS / 'LAB3_Configurations' / BASE_CONFIG,
             repo / 'lab_parser.py', repo / 'parser/glossary.csv']
    for path in paths:
        if not path.is_file():
            raise RuntimeError('Missing file: ' + str(path) +
                               '\nRun this script from your Lab 3 repository root.')
    baseline, assoc, xml_text = [p.read_text(encoding='utf-8-sig') for p in paths[:3]]
    compact = re.sub(r'\s+', '', baseline)
    if '#defineKB1024' not in compact:
        raise RuntimeError('Expected KB=1024 in the Part 7 source.')
    if 'i<MEMORYPOOL_SIZE/4;i+=STRIDE/4' not in compact:
        raise RuntimeError('Unexpected Part 7 benchmark loop; refusing to guess.')
    compact = re.sub(r'\s+', '', assoc)
    if '#defineKB1024' not in compact:
        raise RuntimeError('Expected KB=1024 in the Part 8 source.')
    for fragment in ['i<(MEMORYPOOL_SIZE/2)/4;i+=1',
                     'sum+=mempool[i];', 'sum+=mempool[i+STRIDE/4];']:
        if fragment not in compact:
            raise RuntimeError('Unexpected Part 8 loop: missing ' + fragment)
    tree = ET.fromstring(xml_text)
    l1 = tree.find('./privateCaches/privateCache')
    l2 = tree.find('./sharedCaches/sharedCache')
    expected = [(tree, {'OutOfOrderStages': '1', 'nCores': '1', 'RunTillEnd': '1'}),
                (l1, {'cacheSize': '8192', 'blockSize': '64', 'nways': '1',
                      'ReplcPolc': 'RANDOM', 'mapping': '0'}),
                (l2, {'cacheSize': '16384', 'blockSize': '64', 'nways': '2',
                      'ReplcPolc': 'LRU', 'mapping': '1'})]
    for node, values in expected:
        if node is None:
            raise RuntimeError('Missing cache element in baseline XML.')
        for name, value in values.items():
            if node.get(name) != value:
                raise RuntimeError('Baseline XML: expected {}={}, found {}'.format(
                    name, value, node.get(name)))
    fingerprints = {str(p.relative_to(repo)): digest(p) for p in paths}
    return baseline, assoc, xml_text, fingerprints


def prepare(repo, output, work, sources):
    baseline, assoc, xml_text, _ = sources
    cases = []
    for kb in [4, 8, 16, 32]:
        name = 'cache_test_{}KB_4_2.c'.format(kb)
        source = change_define(baseline, 'MEMORYPOOL_SIZE', '{}*KB'.format(kb))
        source = change_define(source, 'STRIDE', '4')
        source = change_define(source, 'NUM_ITERATIONS', '2')
        cpath = output / 'part7/benchmarks' / name
        cfg = output / 'part7/configurations' / BASE_CONFIG
        write_input(cpath, source)
        write_input(cfg, xml_text)
        cases.append({'id': 'capacity_{}KB'.format(kb), 'part': 7, 'value': '{}KB'.format(kb),
                      'source': cpath, 'config': cfg, 'trace_key': 'capacity_{}KB'.format(kb)})
    assoc = change_define(assoc, 'MEMORYPOOL_SIZE', '16*KB')
    assoc = change_define(assoc, 'STRIDE', '8*KB')
    assoc = change_define(assoc, 'NUM_ITERATIONS', '1')
    # Initialize every integer outside SIM_BEGIN/SIM_END; keep the measured loop intact.
    assoc, count = re.subn(
        r'for\s*\(int\s+i\s*=\s*0;\s*i\s*<\s*MEMORYPOOL_SIZE/4;\s*i\s*\+=\s*STRIDE/4\)',
        'for (int i = 0; i < MEMORYPOOL_SIZE/4; i+=1)', assoc)
    if count != 1:
        raise RuntimeError('Unexpected Part 8 initialization loop; refusing to guess.')
    cpath = output / 'part8/benchmarks' / ASSOC_BM
    write_input(cpath, assoc)
    for ways in [1, 4, 16, 128]:
        tree = ET.fromstring(xml_text)
        l1 = tree.find('./privateCaches/privateCache')
        l1.set('nways', str(ways))
        # The supplied XML uses mapping=0 for direct and mapping=1 for set associative.
        l1.set('mapping', '0' if ways == 1 else '1')
        name = 'lab3_1_8KB_64B_{}_RANDOM_16KB_64_2_LRU.xml'.format(ways)
        cfg = output / 'part8/configurations' / name
        write_input(cfg, ET.tostring(tree, encoding='unicode') + '\n')
        cases.append({'id': 'associativity_{}way'.format(ways), 'part': 8, 'value': ways,
                      'source': cpath, 'config': cfg, 'trace_key': 'associativity'})
    return cases


def analytical_rows(part):
    rows = []
    if part == 7:
        for kb in [4, 8, 16, 32]:
            requests = 2 * kb * 1024 // 4
            misses = (kb * 1024 // 64) * (1 if kb <= 8 else 2)
            hits = requests - misses
            rows.append(['{}KB'.format(kb), requests, hits, misses, hits / requests, ''])
    else:
        # Ideal active-pair retention reference, NOT an exact RANDOM-policy prediction.
        for ways in [1, 4, 16, 128]:
            requests = 4096
            misses = 4096 if ways == 1 else 256
            rows.append([ways, requests, requests - misses, misses,
                         (requests - misses) / requests, ''])
    return rows


def run_logged(command, cwd, stdout, stderr, stdin=None):
    stdout.parent.mkdir(parents=True, exist_ok=True)
    with stdout.open('wb') as out, stderr.open('wb') as err:
        inp = stdin.open('rb') if stdin else subprocess.DEVNULL
        try:
            process = subprocess.run([str(x) for x in command], cwd=str(cwd),
                                     stdin=inp, stdout=out, stderr=err)
        finally:
            if stdin:
                inp.close()
    if process.returncode:
        tail = stderr.read_text(encoding='utf-8', errors='replace')[-2500:]
        raise RuntimeError('Command failed ({}): {}\nLog: {}\n{}'.format(
            process.returncode, ' '.join(str(x) for x in command), stderr, tail))


def trace_benchmark(repo, work, case):
    directory = work / 'traces' / case['trace_key']
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / 'trace_C0.trc.shared'
    marker = directory / 'complete.json'
    signature = digest(case['source'])
    if marker.exists():
        data = json.loads(marker.read_text())
        if data['source_sha256'] != signature or not target.is_file() or target.stat().st_size == 0:
            raise RuntimeError('Saved trace does not match its benchmark: ' + str(directory))
        return directory
    # A new subdirectory prevents Pin from overwriting any older memtrace.out.
    attempt = directory / ('attempt_' + uuid.uuid4().hex[:8])
    attempt.mkdir()
    binary = attempt / 'benchmark_exe'
    run_logged(['gcc', '-o', binary, case['source']], repo,
               attempt / 'gcc.stdout.log', attempt / 'gcc.stderr.log')
    pin = repo / TOOLS / 'pin-3.13-98189-g60a6ef199-gcc-linux/pin'
    module = repo / TOOLS / 'obj-intel64/trace_generator.so'
    run_logged([pin, '-t', module, '-manual', '1', '-thread', '1', '--', binary], attempt,
               attempt / 'pin.stdout.log', attempt / 'pin.stderr.log')
    generated = attempt / 'memtrace.out'
    if not generated.is_file() or generated.stat().st_size == 0:
        raise RuntimeError('Pin produced no memory trace. Check ' + str(attempt / 'pin.stderr.log'))
    if target.exists():
        target.rename(directory / ('previous_trace_' + uuid.uuid4().hex[:8]))
    shutil.copyfile(generated, target)
    write_text(marker, json.dumps({'source_sha256': signature}, indent=2))
    return directory


def collect_statistics(parsed, cleaned, expected_requests=None):
    """Count CPU requests and miss IDs; internal eviction IDs are not requests."""
    seen = set()
    outcomes = {}
    arrivals = set()
    completed = set()
    last = None
    misses = 0
    with parsed.open(encoding='utf-8', newline='') as src, cleaned.open(
            'w', encoding='utf-8', newline='') as dst:
        for line in src:
            if not line.strip() or line in seen:
                continue
            seen.add(line)
            dst.write(line)
            row = next(csv.reader([line]))
            if len(row) != 7:
                raise RuntimeError('Unexpected labdata row: ' + repr(row))
            last = row
            if 'L1: Was the request a miss?,0,1,boolean' in line:
                misses += 1
            label = row[2].strip()
            if row[4] == '0' and label == 'add2q_l':
                arrivals.add(int(row[0]))
            if row[4] == '0' and label in ('respond', 'hitActn'):
                completed.add(int(row[0]))
            if label == 'Miss?' and row[4] == '0':
                if row[6] != 'boolean' or row[5] not in ('0', '1'):
                    raise RuntimeError('Invalid miss outcome: ' + repr(row))
                ident, value = int(row[0]), int(row[5])
                if ident in outcomes and outcomes[ident] != value:
                    raise RuntimeError('Conflicting miss outcomes for request ' + str(ident))
                outcomes[ident] = value
    if last is None or last[6] != 'cycle':
        raise RuntimeError('Missing final cycle row; simulator output may be incomplete.')
    original_requests, cycles = int(last[0]), int(last[5])
    requests = len(arrivals)
    if requests <= 0 or cycles <= 0 or not 0 <= misses <= requests:
        raise RuntimeError('Invalid request, miss, or cycle counts.')
    # MSIProtocol emits Miss?=1 only on misses. Hits have hitActn records instead.
    if not set(outcomes) <= arrivals or sum(outcomes.values()) != misses:
        raise RuntimeError('Miss events do not reconcile with CPU arrivals. Keep the logs for inspection.')
    if not arrivals <= completed:
        raise RuntimeError('Some CPU requests have no response/hit completion event; log is incomplete.')
    if expected_requests is not None and requests != expected_requests:
        raise RuntimeError('Trace has {} requests but simulator processed {}.'.format(
            expected_requests, requests))
    return {'requests': requests, 'hits': requests - misses, 'misses': misses,
            'hit_rate': (requests - misses) / requests, 'cycles': cycles,
            'original_script_requests': original_requests,
            'original_script_hits': original_requests - misses}


def isolate_events(repo, raw, events, diagnostics):
    """Keep build/runtime diagnostics out of the stock numeric event parser.

    Preserve every input line in the raw log. Reject malformed event-looking
    records instead of silently removing possible measurements.
    """
    with (repo / 'parser/glossary.csv').open(encoding='utf-8', newline='') as stream:
        labels = {}
        for row in csv.DictReader(stream):
            exact = row['label']
            labels.setdefault(exact.strip(), set()).add(exact)
    labels.setdefault('termina', {'termina'})
    count = skipped = 0
    ended = False
    with raw.open(encoding='utf-8', errors='replace') as src, \
            events.open('w', encoding='utf-8', newline='\n') as dst, \
            diagnostics.open('w', encoding='utf-8', newline='\n') as other:
        for line_number, line in enumerate(src, 1):
            text = line.strip()
            if not text:
                continue
            if text == 'End':
                if not ended:
                    dst.write('End\n')
                ended = True
                continue
            fields = [field.strip() for field in text.split(',')]
            exact_label = text.split(',')[2] if len(fields) >= 3 else ''
            numeric_id = re.fullmatch(r'-?\d+', fields[0]) is not None
            known_label = len(fields) >= 3 and fields[2] in labels
            if numeric_id or known_label:
                valid = (len(fields) == 5 and numeric_id and
                         all(re.fullmatch(r'-?\d+', fields[i]) for i in (1, 3, 4)))
                if not valid or ended:
                    raise RuntimeError('Malformed or misplaced event at {}:{}: {}'.format(
                        raw, line_number, text))
                if fields[2] not in labels and fields[4] not in ('-1', '-2'):
                    raise RuntimeError('Unknown event label at {}:{}: {}'.format(
                        raw, line_number, fields[2]))
                candidates = labels.get(fields[2], {exact_label})
                if exact_label in candidates:
                    fields[2] = exact_label
                elif len(candidates) == 1:
                    fields[2] = next(iter(candidates))
                else:
                    raise RuntimeError('Ambiguous padded glossary label: ' + repr(exact_label))
                dst.write(','.join(fields) + '\n')
                count += 1
            else:
                other.write(line)
                skipped += 1
    if not count:
        raise RuntimeError('No simulator events found in ' + str(raw) +
                           '. Inspect simulator.stdout.log and the raw log.')
    if skipped:
        say('  Separated {} non-event log lines; preserved in {}'.format(skipped, diagnostics))
    return count


def run_case(repo, output, work, case):
    case_dir = work / 'simulations' / case['id']
    case_dir.mkdir(parents=True, exist_ok=True)
    cached = case_dir / 'complete.json'
    signature = {'source': digest(case['source']), 'config': digest(case['config'])}
    if cached.exists():
        data = json.loads(cached.read_text())
        if data['inputs'] != signature:
            raise RuntimeError('Saved result input mismatch: ' + case['id'])
        say('  Reusing completed case.')
        stats = data['statistics']
    else:
        trace = trace_benchmark(repo, work, case)
        attempt = case_dir / ('attempt_' + uuid.uuid4().hex[:8])
        attempt.mkdir()
        config_arg = case['config'].relative_to(repo).as_posix()
        trace_arg = trace.relative_to(repo).as_posix()
        waf_arg = 'scratch/MultiCoreSimulator --CfgFile={} --BMsPath={} --LogFileGenEnable=0'.format(
            shlex.quote(config_arg), shlex.quote(trace_arg))
        # Simulator logger writes stderr, as in the supplied compile_and_run.sh pipeline.
        raw = attempt / 'events.raw.log'
        run_logged([repo / 'waf', '--run', waf_arg], repo,
                   attempt / 'simulator.stdout.log', raw)
        stdout_text = (attempt / 'simulator.stdout.log').read_text(encoding='utf-8', errors='replace')
        if not re.search(r'Cpu\s+0\s+Simulation End\s+@\s+processor cycle', stdout_text):
            raise RuntimeError('Simulator did not report CPU completion. Inspect ' +
                               str(attempt / 'simulator.stdout.log'))
        events = attempt / 'events.only.log'
        isolate_events(repo, raw, events, attempt / 'non_events.log')
        parsed = attempt / 'labdata_before_dedup.csv'
        run_logged([sys.executable, repo / 'lab_parser.py'], repo,
                   parsed, attempt / 'parser.stderr.log', stdin=events)
        with (trace / 'trace_C0.trc.shared').open() as stream:
            trace_requests = sum(1 for line in stream if line.strip())
        stats = collect_statistics(parsed, attempt / 'labdata.csv', trace_requests)
        write_text(cached, json.dumps({'inputs': signature, 'statistics': stats}, indent=2))
    summary = ('Execution time: {cycles}\ntotal number of requests: {requests}\n'
               'total number of hits: {hits}\ntotal number of misses: {misses}\n'
               'hit rate: {hit_rate:.8f}\n').format(**stats)
    if stats['original_script_requests'] != stats['requests']:
        message = ('Original script would use the final message ID ({}) as the request count. '
                   'Counted {} actual CPU requests instead; eviction messages also consume IDs.').format(
                       stats['original_script_requests'], stats['requests'])
        summary += message + '\n'
        say('  ' + message)
    write_text(output / ('part{}/summaries'.format(case['part'])) / (case['id'] + '.txt'), summary)
    say('  {requests} requests, {hits} hits, {misses} misses, '
        '{hit_rate:.4%} hit rate, {cycles} cycles'.format(**stats))
    return [case['value'], stats['requests'], stats['hits'], stats['misses'],
            stats['hit_rate'], stats['cycles']]


def write_notes(output, results):
    p7 = '''PART 7 - ANALYTICAL METHOD AND COMPARISON
Assume a cold, 8 KB direct-mapped L1, 64-byte lines, an array starting at address 0,
and only the specified array reads. Stride is 4 bytes and there are two passes.
Each line contains 16 integers. Requests = 2 * memory_pool_bytes / 4.
For 4 KB and 8 KB, the whole array fits: misses = memory_pool_bytes / 64.
For 16 KB and 32 KB, sequential scanning evicts lines before their next pass:
misses = 2 * memory_pool_bytes / 64. Hits = requests - misses.
Both spatial and temporal locality are present in the access pattern. The small
pools retain data between passes; the larger pools cannot exploit that reuse in L1.

Measured traces can contain additional accesses around SIM_BEGIN/SIM_END, and
malloc does not guarantee 64-byte alignment. These can add misses. An unaligned
8 KB array occupies 129 lines, so it can also suffer a boundary conflict in L1.
Differences must be interpreted using the actual trace, not adjusted to theory.
'''
    p8 = '''PART 8 - ANALYTICAL METHOD AND COMPARISON
Assume a cold, aligned array and only the measured array reads. The benchmark
alternates between two 8 KB halves of a 16 KB array, for 4096 total requests.
With a direct-mapped 8 KB L1, the two addresses in a pair map to the same line:
each access evicts its partner, giving 4096 misses and zero hits.

The associativity_analytical.csv file is the IDEAL ACTIVE-PAIR RETENTION reference.
With 4, 16 or 128 ways, both active lines can coexist. Assuming replacements retain
the active pair (as LRU would for this pattern), there are 256 compulsory misses,
3840 hits and a 93.75% hit rate. This is NOT an exact prediction for RANDOM.

The actual configurations preserve the lab's RANDOM L1 replacement policy.
When a set fills, RANDOM can evict an active line while inserting its partner,
so additional misses are possible even with a perfectly aligned array.
Under independent uniform random victims and invalid-line-first allocation,
the expected misses are approximately 256 + 64/(ways-1): 277.333 at 4 ways,
260.267 at 16 ways, and 256.504 at 128 ways. This expectation also assumes aligned,
array-only accesses. The repository implements RANDOM with rand() % ways and
checks for an invalid way before replacing a line. Do not attribute every
discrepancy solely to trace overhead.

The legacy benchmark filename is retained from the handout. Its actual defines
are MEMORYPOOL_SIZE=16*KB, STRIDE=8*KB and NUM_ITERATIONS=1. The generated copy
initializes all integers before SIM_BEGIN; the supplied measured loop is unchanged.
L1 mapping is set to 1 for associative cases and 0 for direct mapped, consistently
with the mapping values in the supplied L1/L2 baseline configuration.
'''
    for part, text in [(7, p7), (8, p8)]:
        text += '\nCSV rates are fractions (0.9375 = 93.75%). Execution time is simulated\n'
        text += 'cycles, using the final logged cycle as in compile_and_run.sh. Analytical\n'
        text += 'execution time is intentionally blank. Memory pool labels use KB = 1024 bytes.\n'
        text += ('Requests are distinct L1 add2q_l events from core 0, checked against the\n'
                 'input trace length. Misses are distinct Miss?=1 CPU request IDs after\n'
                 'deduplication. Hits = requests - misses; the simulator does not emit\n'
                 'Miss?=0 for every hit. A missed request can later have a hitActn event\n'
                 'while completing, so hitActn alone is not used to count cache hits.\n'
                 'The original script uses the last message ID as the request count.\n'
                 'Eviction messages also consume IDs (CacheController.cpp), so that\n'
                 'shortcut can overcount. Any difference is recorded in the summaries.\n')
        text += '\nMEASURED COMPARISON (only successfully completed cases)\n'
        theory = {row[0]: row for row in analytical_rows(part)}
        if not results[part]:
            text += 'No experimental results collected yet.\n'
        for row in results[part]:
            ideal = theory[row[0]]
            text += ('{}: measured {} requests, {} misses, {:.6f}% hits, {} cycles; '
                     'ideal reference {} requests, {} misses, {:.6f}% hits. '
                     'Difference: {:+d} requests, {:+d} misses, {:+.6f} percentage points.\n').format(
                         row[0], row[1], row[3], 100*row[4], row[5], ideal[1], ideal[3],
                         100*ideal[4], row[1]-ideal[1], row[3]-ideal[3], 100*(row[4]-ideal[4]))
        write_text(output / ('part{}'.format(part)) / 'comparison_notes.txt', text)


def execute(args):
    repo = Path(args.repo).expanduser().resolve()
    sources = read_inputs(repo)
    if not args.prepare_only:
        for path in [repo / 'waf', repo / TOOLS / 'pin-3.13-98189-g60a6ef199-gcc-linux/pin',
                     repo / TOOLS / 'obj-intel64/trace_generator.so']:
            if not path.is_file():
                raise RuntimeError('Missing runtime file: ' + str(path))
        if shutil.which('gcc') is None:
            raise RuntimeError('gcc was not found. Run this script inside the supplied lab VM.')
        for path in [repo / 'waf', repo / TOOLS / 'pin-3.13-98189-g60a6ef199-gcc-linux/pin']:
            if not os.access(str(path), os.X_OK):
                raise RuntimeError('Not executable: ' + str(path) + '\nUse chmod +x on this file in the VM.')
    run_id = args.resume or (datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:6])
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id):
        raise RuntimeError('Invalid run ID. Use the exact ID printed by a previous batch.')
    work = repo / '.lab3_runs' / run_id
    output = repo / 'submission' / ('parts7_8_' + run_id)
    manifest = {'version': VERSION, 'inputs': sources[3]}
    manifest_path = work / 'manifest.json'
    if args.resume:
        if not manifest_path.is_file() or json.loads(manifest_path.read_text()) != manifest:
            raise RuntimeError('Cannot resume: batch is missing or input files changed. Start a new batch.')
    else:
        work.mkdir(parents=True, exist_ok=False)
        output.mkdir(parents=True, exist_ok=False)
        write_text(manifest_path, json.dumps(manifest, indent=2))
    say('Runner revision: ' + RUNNER_REVISION)
    say('Run ID: ' + run_id)
    say('Submission files: ' + str(output))
    say('Logs and traces: ' + str(work))
    say('Resume command: python3 lab3_parts7_8.py --resume ' + run_id)
    status = output / 'STATUS.txt'
    write_text(status, 'PREPARING\n')
    results = {7: [], 8: []}
    try:
        cases = prepare(repo, output, work, sources)
        for part, stem, label in [(7, 'cache_capacity', 'mempool_size'),
                                  (8, 'associativity', 'way')]:
            write_csv(output / ('part{}'.format(part)) / (stem + '_analytical.csv'),
                      label, analytical_rows(part))
        write_notes(output, results)
        write_text(output / 'INPUTS.json', json.dumps(manifest, indent=2))
        if args.prepare_only:
            write_text(status, 'PREPARED ONLY - no experiments run.\n')
            say('Prepared all eight cases. No simulations were run.')
            return output
        write_text(status, 'RUNNING\n')
        say('Configuring waf...')
        config_logs = work / ('configure_' + uuid.uuid4().hex[:8])
        run_logged([repo / 'waf', 'configure'], repo,
                   config_logs / 'stdout.log', config_logs / 'stderr.log')
        say('Building simulator (compiler messages are saved separately)...')
        build_logs = work / ('build_' + uuid.uuid4().hex[:8])
        run_logged([repo / 'waf', 'build'], repo,
                   build_logs / 'stdout.log', build_logs / 'stderr.log')
        for index, case in enumerate(cases, 1):
            say('[{}/8] {}'.format(index, case['id']))
            row = run_case(repo, output, work, case)
            part = case['part']
            results[part].append(row)
            # The handout names the experimental Part 8 file "associative".
            filename = 'cache_capacity_experimental.csv' if part == 7 else 'associative_experimental.csv'
            write_csv(output / ('part{}'.format(part)) / filename,
                      'mempool_size' if part == 7 else 'way', results[part])
            write_notes(output, results)
        write_text(status, 'COMPLETE - all 8 experimental cases succeeded.\n')
        archive = shutil.make_archive(str(output) + '_results', 'zip',
                                      root_dir=str(output.parent), base_dir=output.name)
        say('\nCOMPLETE: all 8 cases finished.')
        say('Send back this small results ZIP: ' + archive)
        say('Each part has analytical/experimental CSVs, C/XML inputs, summaries and comparison notes.')
        say('Keep commits separate for Part 7 and Part 8. Raw logs stay in .lab3_runs.')
        return output
    except BaseException as error:
        write_text(status, 'INCOMPLETE\n{}\nResume: python3 lab3_parts7_8.py --resume {}\n'.format(
            error, run_id))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--repo', default='.', help='Repository root (default: current directory)')
    parser.add_argument('--prepare-only', action='store_true', help='Create inputs and theory, without running')
    parser.add_argument('--resume', metavar='RUN_ID', help='Continue a prior batch and reuse completed cases')
    args = parser.parse_args()
    try:
        execute(args)
    except KeyboardInterrupt:
        say('\nStopped. Completed cases were saved; use the printed resume command.')
        return 130
    except Exception as error:
        say('\nSTOPPED: ' + str(error))
        say('Existing lab files and completed cases were preserved.')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
