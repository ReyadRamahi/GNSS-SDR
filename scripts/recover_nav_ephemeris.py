#!/usr/bin/env python3
"""Recover rejected LNAV ephemeris from an offline NAV audit, validating against emitted XML."""
import argparse
import copy
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit_directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = Path('/home/rrama28/src/gnss-sdr-0.0.16/src/core/system_parameters/GPS_L1_CA.h')
    header = source.read_text()
    definitions = {}
    for name, body in re.findall(r'const std::vector<std::pair<int32_t, int32_t>> (\w+)\(([^;]+)\);', header):
        definitions[name] = [(int(a), int(b)) for a, b in re.findall(r'\{(\d+),\s*(\d+)\}', body)]
    messages = json.loads((args.audit_directory / 'nav_messages.json').read_text())

    def read(bits, name, signed=False):
        chunks = [bits[start - 1:start - 1 + length] for start, length in definitions[name]]
        binary = ''.join(chunks)
        result = int(binary, 2)
        return result - (1 << len(binary)) if signed and binary[0] == '1' else result

    # Each tuple uses field definitions and scales from the local SDK/source.
    fields = [
        ('M_0',2,'M_0',True,math.pi*2**-31), ('delta_n',2,'DELTA_N',True,math.pi*2**-43),
        ('ecc',2,'ECCENTRICITY',False,2**-33), ('sqrtA',2,'SQRT_A',False,2**-19),
        ('OMEGA_0',3,'OMEGA_0',True,math.pi*2**-31), ('i_0',3,'I_0',True,math.pi*2**-31),
        ('omega',3,'OMEGA',True,math.pi*2**-31), ('OMEGAdot',3,'OMEGA_DOT',True,math.pi*2**-43),
        ('idot',3,'I_DOT',True,math.pi*2**-43), ('Cuc',2,'C_UC',True,2**-29),
        ('Cus',2,'C_US',True,2**-29), ('Crc',3,'C_RC',True,2**-5), ('Crs',2,'C_RS',True,2**-5),
        ('Cic',3,'C_IC',True,2**-29), ('Cis',3,'C_IS',True,2**-29),
        ('toe',2,'T_OE',False,16), ('toc',1,'T_OC',False,16),
        ('af0',1,'A_F0',True,2**-31), ('af1',1,'A_F1',True,2**-43), ('af2',1,'A_F2',True,2**-55),
        ('WN',1,'GPS_WEEK',False,1), ('IODE_SF2',2,'IODE_SF2',False,1),
        ('IODE_SF3',3,'IODE_SF3',False,1), ('code_on_L2',1,'CA_OR_P_ON_L2',False,1),
        ('L2_P_data_flag',1,'L2_P_DATA_FLAG',False,1), ('SV_accuracy',1,'SV_ACCURACY',False,1),
        ('SV_health',1,'SV_HEALTH',False,1), ('TGD',1,'T_GD',True,2**-31), ('IODC',1,'IODC',False,1),
        ('AODO',2,'AODO',False,900), ('fit_interval_flag',2,'FIT_INTERVAL_FLAG',False,1),
        ('integrity_status_flag',3,'INTEGRITY_STATUS_FLAG',False,1),
        ('alert_flag',3,'ALERT_FLAG',False,1), ('antispoofing_flag',3,'ANTI_SPOOFING_FLAG',False,1),
    ]
    decoded = {}
    for prn in sorted({m['prn'] for m in messages}):
        selected = {sf: [m for m in messages if m['prn'] == prn and m['subframe'] == sf] for sf in [1,2,3]}
        if not all(selected.values()):
            continue
        bits = {sf: selected[sf][-1]['nav_message'] for sf in selected}
        values = {field: read(bits[sf], name, signed)*scale for field,sf,name,signed,scale in fields}
        iodc, iode2, iode3 = (int(values[k]) for k in ['IODC','IODE_SF2','IODE_SF3'])
        if not (iode2 == iode3 == (iodc & 255)) or values['SV_health'] != 0:
            raise SystemExit(f'PRN {prn}: inconsistent issue-of-data or unhealthy satellite')
        values.update(PRN=prn, tow=max(selected[sf][-1]['tow_next_subframe_s'] for sf in selected),
                      satClkDrift=0.0, dtr=0.0, spare1=0.0, spare2=0.0)
        decoded[prn] = values

    tree = ET.parse(args.audit_directory / 'gps_ephemeris.xml')
    root = tree.getroot()
    mapping = root.find('GNSS-SDR_ephemeris_map')
    if mapping is None:
        raise SystemExit('Missing native ephemeris map')
    native = {int(item.findtext('first')): item for item in mapping.findall('item')}
    comparisons = {}
    for prn, item in native.items():
        values = decoded[prn]
        second = item.find('second')
        tested = []
        for field, value in values.items():
            if field in ['tow','satClkDrift','dtr']:
                continue
            actual = second.findtext(field)
            if actual is None or not math.isclose(float(actual), value, rel_tol=1e-12, abs_tol=1e-18):
                raise SystemExit(f'Independent NAV decode differs from native XML for PRN {prn}, {field}: {actual} vs {value}')
            tested.append(field)
        comparisons[prn] = len(tested)
    if len(comparisons) < 2:
        raise SystemExit('Need at least two native ephemerides for cross-validation')
    added = []
    for prn in sorted(decoded.keys() - native.keys()):
        values = decoded[prn]
        if int(values['IODC']) <= 255:
            raise SystemExit(f'PRN {prn}: rejection is not the investigated high-IODC case')
        template = copy.deepcopy(next(iter(native.values())).find('second'))
        template.attrib.clear()
        for child in template:
            if child.tag not in values:
                raise SystemExit(f'No decoded or defined value for XML field {child.tag}')
            child.text = str(values[child.tag])
        item = ET.SubElement(mapping, 'item')
        ET.SubElement(item, 'first').text = str(prn)
        item.append(template)
        added.append(prn)
    mapping.find('count').text = str(len(mapping.findall('item')))
    args.output.write_text('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n<!DOCTYPE boost_serialization>\n' + ET.tostring(root, encoding='unicode') + '\n')
    provenance = {'nav_audit_directory':str(args.audit_directory.resolve()), 'field_definition_source':str(source),
                  'native_prns_cross_validated':comparisons, 'added_prns':added,
                  'added_issue_of_data':{prn:{k:decoded[prn][k] for k in ['IODC','IODE_SF2','IODE_SF3']} for prn in added},
                  'note':'Experimental data-only workaround from decoded NAV in this recording; no receiver software or hardware changes.'}
    args.output.with_suffix('.provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(json.dumps(provenance,indent=2))


if __name__ == '__main__':
    main()
