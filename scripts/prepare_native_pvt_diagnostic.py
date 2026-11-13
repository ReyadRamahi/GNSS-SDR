#!/usr/bin/env python3
"""Prepare an isolated native receiver build; refuse dependency fetching.

This performs configuration and dependency probes only, never installation,
RF capture, receiver execution, or a solver behavior change.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = Path('/home/rrama28/src/gnss-sdr-0.0.16')


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    previous = ROOT / 'runs/first_epoch_pvt_20261108_4'
    inputs = list(json.loads((previous / 'input_hashes_before.json').read_text()))
    inputs += [str(ROOT / 'runs/rx1h_pvt_lowmask_cs0kpzfz/config_used.conf'),
               '/usr/bin/gnss-sdr', str(ORIGINAL / 'CMakeLists.txt'),
               str(ORIGINAL / 'src/algorithms/PVT/libs/rtklib_solver.cc'),
               str(ORIGINAL / 'src/algorithms/libs/rtklib/rtklib_pntpos.cc')]
    before = {name: sha256(Path(name)) for name in inputs}
    (out / 'input_hashes_before.json').write_text(json.dumps(before, indent=2) + '\n')
    source = out / 'source'
    shutil.copytree(ORIGINAL, source, symlinks=True,
                    ignore=shutil.ignore_patterns('build', '.git', '__pycache__'))
    patches = out / 'patches'
    patches.mkdir()
    # Logging changes only. Keep the proposed error-copy correction unapplied.
    for name, cwd in [('proposed_boundary_logging.patch', source),
                      ('logging_only.patch', source / 'src/algorithms/libs/rtklib')]:
        patch = previous / name
        shutil.copy2(patch, patches / name)
        result = subprocess.run(['patch', '--batch', '--forward', '-p1'],
                                input=patch.read_text(), text=True, cwd=cwd,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
        (out / (name + '.apply.log')).write_text(result.stdout)
    shutil.copy2(previous / 'proposed_error_propagation.patch', patches)

    # Native CMake has automatic Git/URL dependency fallbacks. Guard every
    # top-level ExternalProject declaration before allowing configuration.
    cmake_path = source / 'CMakeLists.txt'
    original_cmake = cmake_path.read_text()
    guarded = original_cmake.replace('ExternalProject_Add(', 'offline_external_project_add(')
    guard = '''
# Isolated diagnostic build: dependency downloads are forbidden.
function(offline_external_project_add dependency)
    foreach(keyword GIT_REPOSITORY URL SVN_REPOSITORY HG_REPOSITORY CVS_REPOSITORY)
        list(FIND ARGN "${keyword}" found)
        if(NOT found EQUAL -1)
            message(FATAL_ERROR "OFFLINE_DEPENDENCY_BLOCKER: ${dependency} needs ${keyword}; fetching is forbidden")
        endif()
    endforeach()
    ExternalProject_Add(${dependency} ${ARGN})
endfunction()
'''
    guarded = guarded.replace('include(ExternalProject)', 'include(ExternalProject)\n' + guard)
    cmake_path.write_text(guarded)
    (patches / 'no_dependency_fetch.patch').write_text(''.join(difflib.unified_diff(
        original_cmake.splitlines(True), guarded.splitlines(True),
        fromfile='a/CMakeLists.txt', tofile='b/CMakeLists.txt')))

    probes = {}
    for name, header in [('protobuf', 'google/protobuf/message.h'),
                         ('pugixml', 'pugixml.hpp')]:
        command = ['c++', '-x', 'c++', '-E', '-']
        result = subprocess.run(command, input='#include <' + header + '>\n',
                                text=True, stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE, timeout=15)
        probes[name] = {'command': command, 'header': header,
                        'returncode': result.returncode, 'stderr': result.stderr}
    probes['protoc'] = {'path': shutil.which('protoc')}
    for name, directory in [
            ('cached_protobuf_source', ORIGINAL / 'build/thirdparty/protobuf'),
            ('cached_pugixml_source', ORIGINAL / 'build/thirdparty/pugixml')]:
        probes[name] = {'directory': str(directory),
                        'regular_files': [str(p.relative_to(directory))
                                          for p in directory.rglob('*') if p.is_file()]}
    (out / 'dependency_probes.json').write_text(json.dumps(probes, indent=2) + '\n')
    build = out / 'build'
    command = ['cmake', '-S', str(source), '-B', str(build),
               '-DCMAKE_BUILD_TYPE=Release', '-DPYTHON_EXECUTABLE=/usr/bin/python3',
               '-DENABLE_UHD=OFF', '-DENABLE_OSMOSDR=OFF', '-DENABLE_LIMESDR=OFF',
               '-DENABLE_UNIT_TESTING=OFF', '-DENABLE_UNIT_TESTING_EXTRA=OFF',
               '-DENABLE_SYSTEM_TESTING=OFF', '-DENABLE_SYSTEM_TESTING_EXTRA=OFF',
               '-DENABLE_GNSS_SIM_INSTALL=OFF', '-DENABLE_OWN_GPSTK=OFF',
               '-DENABLE_OWN_GLOG=OFF', '-DENABLE_OWN_ARMADILLO=OFF',
               '-DENABLE_OWN_CPUFEATURES=OFF', '-DENABLE_PROFILING=OFF',
               '-DENABLE_BENCHMARKS=OFF', '-DENABLE_EXTERNAL_MATHJAX=OFF']
    (out / 'configure_command.json').write_text(json.dumps(command, indent=2) + '\n')
    with (out / 'configure.log').open('w') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=120)
    after = {name: sha256(Path(name)) for name in inputs}
    assert before == after
    (out / 'input_hashes.json').write_text(json.dumps(
        {'before': before, 'after': after, 'unchanged': before == after}, indent=2) + '\n')
    status = {'configuration_returncode': result.returncode,
              'source_copy': str(source), 'receiver_built': False,
              'receiver_executed': False, 'solver_behavior_changed': False,
              'error_copy_patch_applied': False, 'original_inputs_unchanged': True}
    (out / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps(status, indent=2))
    print('Configuration log:', out / 'configure.log')


if __name__ == '__main__':
    main()
