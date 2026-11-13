#!/usr/bin/env python3
"""Build isolated baseline/candidate standalone solvers from existing local files.

No package changes, installed receiver changes, download or native receiver build.
The output directory must be fresh. Both binaries read the saved full observables
dump directly; mode first selects only GPS TOW 14052.000.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'runs/native_pvt_confirmation_recheck/source/src'
PRIOR=ROOT/'runs/first_epoch_pvt_20261108_4'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    pristine=out/'pristine_rtklib';pristine.mkdir(exist_ok=False)
    for p in (PRIOR/'working_copy').glob('rtklib*'):
        if p.suffix in ['.h','.cc']:shutil.copy2(p,pristine/p.name)
    p=pristine/'rtklib_pntpos.cc'
    clean=p.read_text()
    clean='\n'.join(l for l in clean.splitlines() if not ('std::fprintf(stderr,' in l and any(t in l for t in ['EPOCH iter=','FILTER iter=','COUNT iter=','ESTPOS failure'])))+'\n'
    clean=clean.replace('#include <cstdio>\n','')
    expected=json.loads((PRIOR/'source_provenance.json').read_text())['rtklib_pntpos.cc']['original_sha256']
    assert hashlib.sha256(clean.encode()).hexdigest()==expected
    p.write_text(clean)
    core=out/'core';core.mkdir()
    for p in (SOURCE/'core/system_parameters').glob('*.h'):shutil.copy2(p,core/p.name)
    for n in ['gps_ephemeris.cc','gnss_satellite.cc']:shutil.copy2(SOURCE/'core/system_parameters'/n,core/n)
    shutil.copy2(ROOT/'scripts/epoch_window_harness.cc',out/'epoch_window_harness.cc')

    # Diagnostics-only correction, common to both binaries.
    error_fixed=clean.replace('    msg = msg_aux;\n\n    return 0;',
                            '    std::snprintf(msg, 128, "%s", msg_aux);\n\n    return 0;')
    assert error_fixed!=clean
    (out/'error_copy_only.patch').write_text(''.join(difflib.unified_diff(clean.splitlines(True),error_fixed.splitlines(True),fromfile='a/rtklib_pntpos.cc',tofile='b/rtklib_pntpos.cc')))
    # Behavior candidate: defer only elevation selection until LS convergence of
    # an observation-derived provisional position, then solve with original opt.
    phase_anchor='    for (i = 0; i < MAXITR; i++)\n        {\n            /* pseudorange residuals */'
    phase_code='''    bool provisional_position = norm_rtk(x, 3) == 0.0;
    prcopt_t provisional_opt = *opt;
    provisional_opt.elmin = -GNSS_PI / 2.0;

'''
    candidate=error_fixed.replace(phase_anchor,phase_code+phase_anchor)
    old='nv = rescode(i, obs, n, rs, dts, vare, svh, nav, x, opt, v, H, var, azel, vsat, resp, &ns);'
    new='nv = rescode(i, obs, n, rs, dts, vare, svh, nav, x, provisional_position ? &provisional_opt : opt, v, H, var, azel, vsat, resp, &ns);'
    candidate=candidate.replace(old,new)
    anchor='''            if (norm_rtk(dx, NX) < 1e-4)
                {
                    sol->type = 0;'''
    replacement='''            if (norm_rtk(dx, NX) < 1e-4)
                {
                    if (provisional_position)
                        {
                            provisional_position = false;
                            continue;  // Recompute with the configured mask before validation.
                        }
                    sol->type = 0;'''
    assert anchor in candidate and phase_anchor in error_fixed
    candidate=candidate.replace(anchor,replacement)
    (out/'provisional_position_only.patch').write_text(''.join(difflib.unified_diff(error_fixed.splitlines(True),candidate.splitlines(True),fromfile='a/rtklib_pntpos.cc',tofile='b/rtklib_pntpos.cc')))

    def instrument(s,is_candidate):
        s=s.replace('#include <cstring>','#include <cstring>\n#include <cstdio>')
        cond='std::fabs(time2gpst(obs[0].time, nullptr) - 14052.0) < 1e-6'
        s=s.replace('ecef2pos(rr, pos);','ecef2pos(rr, pos);\n    if ('+cond+') std::fprintf(stderr, "STATE iter=%d x=%.12f %.12f %.12f clock_m=%.12f\\n", iter, rr[0], rr[1], rr[2], dtr);',1)
        s=s.replace('if (elaux < opt->elmin)',
          'if ('+cond+') std::fprintf(stderr, "ELEV iter=%d prn=%d elevation_deg=%.12f effective_mask_deg=%.12f passes=%d\\n", iter, obs[i].sat, elaux*R2D, opt->elmin*R2D, elaux >= opt->elmin);\n            if (elaux < opt->elmin)')
        phase='provisional_position ? "provisional" : "configured"' if is_candidate else '"configured"'
        s=s.replace('            if (nv < NX)',
          '            if ('+cond+') std::fprintf(stderr, "COUNTS iter=%d phase=%s n=%d ns=%d nv=%d required=%d\\n", i, '+phase+', n, ns, nv, NX);\n            if (nv < NX)')
        s=s.replace('    std::snprintf(msg, 128, "%s", msg_aux);',
          '    if ('+cond+') std::fprintf(stderr, "FAIL iter=%d ns=%d nv=%d reason=%s\\n", i, ns, nv, msg_aux);\n    std::snprintf(msg, 128, "%s", msg_aux);')
        return s
    baseline=instrument(error_fixed,False);fixed=instrument(candidate,True)
    (out/'baseline_pntpos.cc').write_text(baseline)
    (out/'candidate_pntpos.cc').write_text(fixed)
    for n,a,b in [('baseline_logging.patch',error_fixed,baseline),('candidate_logging.patch',candidate,fixed)]:
        (out/n).write_text(''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/rtklib_pntpos.cc',tofile='b/rtklib_pntpos.cc')))
    flags=['g++','-std=c++17','-O1','-ffunction-sections','-fdata-sections','-I'+str(pristine),'-I'+str(core)]
    units=[out/'epoch_window_harness.cc']+[pristine/('rtklib_'+u+'.cc') for u in ['rtkcmn','ephemeris','preceph','sbas','ionex','conversions']]+[core/'gps_ephemeris.cc',core/'gnss_satellite.cc']
    objects=out/'objects';objects.mkdir()
    commands=[]
    with (out/'build.log').open('w') as log:
        for source in units+[out/'baseline_pntpos.cc',out/'candidate_pntpos.cc']:
            obj=objects/(source.stem+'.o');cmd=flags+['-c',str(source),'-o',str(obj)];commands.append(cmd)
            subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=120,check=True)
        common=[str(objects/(p.stem+'.o')) for p in units]
        for label in ['baseline','candidate']:
            cmd=['g++']+common+[str(objects/(label+'_pntpos.o')),'-Wl,--gc-sections','-lglog','-lgflags','-lboost_serialization','-llapack','-lblas','-lpthread','-o',str(out/(label+'_epoch_window'))]
            commands.append(cmd);subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=30,check=True)
    (out/'build_commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    print(out,flush=True)


if __name__=='__main__':main()
