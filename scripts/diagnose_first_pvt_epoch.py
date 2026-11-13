#!/usr/bin/env python3
"""Extract one saved epoch and diagnose it with an isolated local RTKLIB copy.

No receiver executable, SDR, network, or installed software is changed or opened.
The source copy has logging-only instrumentation. This is a reconstruction, not
proof of an installed GNSS-SDR fix. Inputs are read-only and hashed before/after.
"""
import argparse
import difflib
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('/home/rrama28/src/gnss-sdr-0.0.16')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def semantic(node):
    return [node.tag, node.attrib, (node.text or '').strip(),
            [semantic(c) for c in node]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    run = ROOT / 'runs/rx1h_four_prn_axlbe7v2'
    audit = ROOT / 'runs/nav_audit_9dvjj0co'
    inputs = [ROOT / 'runs/rx1h_baseline_20261108_035309_7qbMJ8/rx1h.cf32',
              run / 'observables.dat', run / 'config_used.conf',
              run / 'gps_ephemeris.xml', run / 'independent_position_check.json',
              run / 'gps_iono.xml', run / 'gps_utc_model.xml', audit / 'nav_messages.json',
              audit / 'gps_ephemeris.xml', audit / 'recovered_ephemeris.xml',
              audit / 'gps_iono.xml', audit / 'gps_utc_model.xml']
    before = {str(p): digest(p) for p in inputs}
    (out / 'input_hashes_before.json').write_text(json.dumps(before, indent=2) + '\n')
    data = (run / 'observables.dat').read_bytes()
    size = 4 * 7 * 8
    assert len(data) % size == 0
    counts = {}
    first = None
    for index in range(len(data) // size):
        epoch = [struct.unpack_from('<7d', data, index * size + ch * 56) for ch in range(4)]
        valid = sum(int(row[6] == 1) for row in epoch)
        counts[valid] = counts.get(valid, 0) + 1
        if valid == 4 and first is None:
            first = (index, epoch)
    index, epoch = first
    names = ['RX_time_s', 'interp_TOW_s', 'Carrier_Doppler_hz',
             'Carrier_phase_cycles', 'Pseudorange_m', 'PRN', 'Flag_valid_pseudorange']
    extraction = {'epoch_index_zero_based': index, 'byte_offset': index * size,
                  'epoch_bytes': size, 'valid_count_distribution': counts,
                  'channels': [dict(channel=ch, **dict(zip(names, row))) for ch, row in enumerate(epoch)],
                  'not_saved': ['CN0_dB_hz', 'Flag_valid_acquisition', 'Flag_valid_word',
                                'Flag_valid_symbol_output', 'Flag_PLL_180_deg_phase_locked']}
    (out / 'epoch.json').write_text(json.dumps(extraction, indent=2) + '\n')
    (out / 'epoch.bin').write_bytes(data[index * size:(index + 1) * size])

    native = ET.parse(audit / 'gps_ephemeris.xml').getroot()
    recovered = ET.parse(audit / 'recovered_ephemeris.xml').getroot()
    def items(root):
        return {int(i.findtext('first')): i for i in root.find('GNSS-SDR_ephemeris_map').findall('item')}
    old, new = items(native), items(recovered)
    xml_audit = {'experimental': True, 'native_prns': list(old), 'recovered_prns': list(new),
                 'existing_items_exact_semantic_match': {p: semantic(old[p]) == semantic(new[p]) for p in old},
                 'count_change': [len(old), len(new)],
                 'added_items': {p: {c.tag: c.text for c in new[p].find('second')} for p in new.keys() - old.keys()}}
    # Remove precisely the added records and restore count, then compare the entire tree.
    normalized = ET.fromstring(ET.tostring(recovered))
    mapping = normalized.find('GNSS-SDR_ephemeris_map')
    for item in list(mapping.findall('item')):
        if int(item.findtext('first')) not in old:
            mapping.remove(item)
    mapping.find('count').text = str(len(old))
    xml_audit['whole_tree_unchanged_after_removing_addition_and_restoring_count'] = semantic(native) == semantic(normalized)
    end = items(ET.parse(run / 'gps_ephemeris.xml').getroot())
    xml_audit['end_of_replay_field_differences_from_assistance'] = {
        p: {c.tag: [new[p].find('second').findtext(c.tag), c.text]
            for c in item.find('second') if c.text != new[p].find('second').findtext(c.tag)}
        for p, item in end.items()}
    xml_audit['end_of_replay_numeric_differences_from_assistance'] = {
        p: {c.tag: [float(new[p].find('second').findtext(c.tag)), float(c.text)]
            for c in item.find('second')
            if float(c.text) != float(new[p].find('second').findtext(c.tag))}
        for p, item in end.items()}
    xml_audit['unchanged_iono_utc_between_audit_and_replay'] = {
        name: semantic(ET.parse(audit / name).getroot()) == semantic(ET.parse(run / name).getroot())
        for name in ['gps_iono.xml', 'gps_utc_model.xml']}
    regenerated = out / 'experimental_regenerated.xml'
    with (out / 'experimental_regeneration.log').open('w') as log:
        subprocess.run(['python3', str(ROOT / 'scripts/recover_nav_ephemeris.py'),
                        str(audit), '--output', str(regenerated)],
                       stdout=log, stderr=subprocess.STDOUT, timeout=15, check=True)
    xml_audit['regenerated_experimental_xml_byte_identical'] = regenerated.read_bytes() == (audit / 'recovered_ephemeris.xml').read_bytes()
    (out / 'xml_audit.json').write_text(json.dumps(xml_audit, indent=2) + '\n')
    (out / 'xml.diff').write_text(''.join(difflib.unified_diff(
        (audit / 'gps_ephemeris.xml').read_text().splitlines(True),
        (audit / 'recovered_ephemeris.xml').read_text().splitlines(True),
        fromfile='native.xml', tofile='experimental_recovered.xml')))

    working = out / 'working_copy'
    working.mkdir()
    ion = ET.parse(audit / 'gps_iono.xml').getroot().find('GNSS-SDR_iono_model')
    ion_values = [float(ion.findtext(k)) for k in
                  ['alpha0', 'alpha1', 'alpha2', 'alpha3', 'beta0', 'beta1', 'beta2', 'beta3']]
    (working / 'iono_values.h').write_text('const double saved_ion[8] = {' +
                                         ','.join(map(repr, ion_values)) + '};\n')
    independent = json.loads((run / 'independent_position_check.json').read_text())['epochs'][0]
    assert independent['receiver_tow_s'] == epoch[0][0]
    llh = [math.radians(independent['latitude_deg']), math.radians(independent['longitude_deg']),
           independent['ellipsoidal_height_m']]
    (working / 'independent_seed.h').write_text('const double independent_llh[3] = {' +
                                               ','.join(map(repr, llh)) + '};\n')
    lib = SOURCE / 'src/algorithms/libs/rtklib'
    for path in lib.iterdir():
        if path.suffix in ['.h', '.cc']:
            shutil.copy2(path, working / path.name)
    pnt = working / 'rtklib_pntpos.cc'
    original = pnt.read_text()
    modified = original.replace('#include <cstring>', '#include <cstring>\n#include <cstdio>')
    modified = modified.replace('ecef2pos(rr, pos);',
        'ecef2pos(rr, pos);\n    std::fprintf(stderr, "EPOCH iter=%d x=%.9f %.9f %.9f clock_m=%.9f\\n", iter, rr[0], rr[1], rr[2], dtr);', 1)
    modified = modified.replace('if (elaux < opt->elmin)',
        'std::fprintf(stderr, "FILTER iter=%d sat=%d el_deg=%.9f mask_deg=%.9f\\n", iter, obs[i].sat, elaux*R2D, opt->elmin*R2D);\n            if (elaux < opt->elmin)')
    modified = modified.replace('if (nv < NX)',
        'std::fprintf(stderr, "COUNT iter=%d ns=%d nv=%d required=%d\\n", i, ns, nv, NX);\n            if (nv < NX)')
    modified = modified.replace('    msg = msg_aux;\n\n    return 0;',
        '    std::fprintf(stderr, "ESTPOS failure iter=%d detail=%s\\n", i, msg_aux);\n    msg = msg_aux;\n\n    return 0;')
    pnt.write_text(modified)
    (out / 'logging_only.patch').write_text(''.join(difflib.unified_diff(
        original.splitlines(True), modified.splitlines(True),
        fromfile='a/rtklib_pntpos.cc', tofile='b/rtklib_pntpos.cc')))
    shutil.copy2(ROOT / 'scripts/first_pvt_epoch.cc', working / 'first_pvt_epoch.cc')
    units = ['rtkcmn', 'ephemeris', 'preceph', 'sbas', 'ionex', 'pntpos', 'conversions']
    command = ['g++', '-std=c++17', '-O1', '-ffunction-sections', '-fdata-sections',
               '-I' + str(working), '-I' + str(SOURCE / 'src/core/system_parameters'),
               str(working / 'first_pvt_epoch.cc')]
    command += [str(working / ('rtklib_' + u + '.cc')) for u in units]
    command += [str(SOURCE / 'build/src/core/system_parameters/libcore_system_parameters.a'),
                '-Wl,--gc-sections', '-lglog', '-lgflags', '-lboost_serialization',
                '-llapack', '-lblas', '-lpthread', '-o', str(out / 'first_pvt_epoch')]
    (out / 'compile_command.json').write_text(json.dumps(command, indent=2) + '\n')
    with (out / 'build.log').open('w') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=120, check=True)
    command = [str(out / 'first_pvt_epoch'), str(out / 'epoch.bin'),
               str(audit / 'recovered_ephemeris.xml'), str(audit / 'gps_iono.xml')]
    commands = []
    for name, extra in [('native_path_trace.log', []), ('existing_3deg_trace.log', ['3']),
                        ('existing_3deg_seeded_diagnostic.log', ['3', 'seed_from_independent'])]:
        commands.append(command + extra)
        with (out / name).open('w') as log:
            subprocess.run(command + extra, stdout=log, stderr=subprocess.STDOUT, timeout=15, check=True)
    (out / 'run_commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    after = {str(p): digest(p) for p in inputs}
    (out / 'input_hashes.json').write_text(json.dumps({'before': before, 'after': after,
                                                    'unchanged': before == after}, indent=2) + '\n')
    assert before == after
    print(out)


if __name__ == '__main__':
    main()
