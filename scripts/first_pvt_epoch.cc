// Isolated single-epoch diagnostic: calls the existing local GPS conversions,
// satellite propagation and point-position solver. No RF or receiver flowgraph.
#include <boost/archive/xml_iarchive.hpp>
#include <boost/serialization/map.hpp>
#include <glog/logging.h>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include "gps_ephemeris.h"
#include "gnss_synchro.h"
#include "rtklib_conversions.h"
#include "rtklib_rtkcmn.h"
#include "rtklib_ephemeris.h"
#include "rtklib_pntpos.h"
#include "iono_values.h"
#include "independent_seed.h"

int main(int argc, char** argv) {
    if (argc < 4 || argc > 6) return 2;
    const double mask = argc >= 5 ? std::stod(argv[4]) : 15;
    if (mask != 15 && mask != 3) return 2; // Only the two already saved configurations.
    const bool seeded = argc == 6 && std::string(argv[5]) == "seed_from_independent";
    if (argc == 6 && !seeded) return 2;
    google::InitGoogleLogging(argv[0]);
    FLAGS_logtostderr = true;
    FLAGS_v = 4;
    std::cout << std::setprecision(17);
    std::map<int, Gps_Ephemeris> gps;
    { std::ifstream f(argv[2]); boost::archive::xml_iarchive ar(f);
      ar >> boost::serialization::make_nvp("GNSS-SDR_ephemeris_map", gps); }
    obsd_t obs[4]{};
    eph_t eph[4]{};
    std::ifstream f(argv[1], std::ios::binary);
    for (int ch=0; ch<4; ++ch) {
        double d[7]; f.read(reinterpret_cast<char*>(d), sizeof(d));
        if (!f || d[6] != 1) return 3;
        const auto& e = gps.at(static_cast<int>(d[5]));
        Gnss_Synchro s;
        s.System='G'; s.Signal[0]='1'; s.Signal[1]='C'; s.PRN=d[5];
        s.Channel_ID=ch; s.RX_time=d[0]; s.interp_TOW_ms=d[1]*1000;
        s.Carrier_Doppler_hz=d[2]; s.Carrier_phase_rads=d[3]*TWO_PI;
        s.Pseudorange_m=d[4]; s.Flag_valid_pseudorange=true;
        // CN0 and other flags are not saved; SNR masking is disabled in the
        // receiver's PVT adapter. These zero defaults cannot reject this epoch.
        insert_obs_to_rtklib(obs[ch],s,e.WN,0,false);
        eph[ch]=eph_to_rtklib(e,false);
        std::cout << "INPUT ch=" << ch << " prn=" << s.PRN << " RX=" << s.RX_time
                  << " tx_tag=" << d[1] << " P=" << obs[ch].P[0]
                  << " week=" << eph[ch].week << " toe=" << eph[ch].toes
                  << " XML_health=" << e.SV_health << " XML_IODC=" << e.IODC
                  << " XML_IODE=" << e.IODE_SF2 << " RTK_svh=" << eph[ch].svh
                  << " RTK_iode=" << eph[ch].iode << " RTK_iodc=" << eph[ch].iodc << '\n';
    }
    auto nav = std::make_unique<nav_t>();
    nav->eph=eph; nav->n=4;
    // Exact saved XML coefficients, extracted by the Python driver.
    for (int j=0;j<8;++j) nav->ion_gps[j]=saved_ion[j];
    for (int i=0;i<MAXSAT;++i) for(int j=0;j<NFREQ;++j)
        nav->lam[i][j]=satwavelen(i+1,j,nav.get());
    prcopt_t opt{};
    // Relevant options from rtklib_pvt.cc and the saved configuration.
    opt.mode=PMODE_SINGLE; opt.nf=1; opt.navsys=SYS_GPS;
    opt.elmin=mask*D2R; opt.sateph=EPHOPT_BRDC;
    opt.ionoopt=IONOOPT_BRDC; opt.tropopt=TROPOPT_SAAS;
    opt.eratio[0]=opt.eratio[1]=opt.eratio[2]=100;
    opt.err[0]=100; opt.err[1]=opt.err[2]=0.003; opt.err[4]=1;
    opt.maxgdop=30;
    sol_t sol{};
    if (seeded) {
        // Aided diagnostic only. This is neither an independent solution nor a
        // native receiver fix. It tests sensitivity to solver initialization.
        pos2ecef(independent_llh, sol.rr);
    }
    char msg[256]{};
    std::cout << "NATIVE_POINT_POSITION_BEGIN initial_ECEF=" << sol.rr[0] << ','
              << sol.rr[1] << ',' << sol.rr[2] << " mask_deg=" << mask
              << " seeded_from_independent=" << seeded << '\n' << std::flush;
    const int result=pntpos(obs,4,nav.get(),&opt,&sol,nullptr,nullptr,msg);
    std::cout << "NATIVE_POINT_POSITION_END result=" << result << " status="
              << int(sol.stat) << " caller_error='" << msg << "' ECEF="
              << sol.rr[0] << ',' << sol.rr[1] << ',' << sol.rr[2] << '\n';
    double llh[3]{}; ecef2pos(sol.rr,llh);
    std::cout << "RESULT_LLH=" << llh[0]*R2D << ',' << llh[1]*R2D << ',' << llh[2]
              << " clock_bias_s=" << sol.dtr[0] << " ns=" << int(sol.ns) << '\n';
    return 0;
}
