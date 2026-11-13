// Standalone reconstruction of saved Observables output. Never opens an SDR.
#include <boost/archive/xml_iarchive.hpp>
#include <boost/serialization/map.hpp>
#include <boost/property_tree/ptree.hpp>
#include <boost/property_tree/xml_parser.hpp>
#include <glog/logging.h>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <string>
#include "gps_ephemeris.h"
#include "gnss_synchro.h"
#include "rtklib_conversions.h"
#include "rtklib_rtkcmn.h"
#include "rtklib_pntpos.h"

int main(int argc, char** argv) {
    if (argc != 7) return 2;
    const std::string mode=argv[5];
    const double mask=std::stod(argv[6]);
    if (mode!="first" && mode!="cold" && mode!="sequential") return 2;
    google::InitGoogleLogging(argv[0]);
    FLAGS_logtostderr=true; FLAGS_v=0;
    std::cout << std::setprecision(17);
    std::map<int,Gps_Ephemeris> gps;
    { std::ifstream file(argv[2]); boost::archive::xml_iarchive ar(file);
      ar >> boost::serialization::make_nvp("GNSS-SDR_ephemeris_map",gps); }
    boost::property_tree::ptree ion;
    boost::property_tree::read_xml(argv[3],ion);
    const char* ion_names[]={"alpha0","alpha1","alpha2","alpha3","beta0","beta1","beta2","beta3"};
    prcopt_t opt{};
    opt.mode=PMODE_SINGLE; opt.nf=1; opt.navsys=SYS_GPS;
    opt.elmin=mask*D2R; opt.sateph=EPHOPT_BRDC;
    opt.ionoopt=IONOOPT_BRDC; opt.tropopt=TROPOPT_SAAS;
    opt.eratio[0]=opt.eratio[1]=opt.eratio[2]=100;
    opt.err[0]=100; opt.err[1]=opt.err[2]=0.003; opt.err[4]=1;
    opt.maxgdop=30;
    std::ifstream input(argv[1],std::ios::binary);
    std::ofstream output(argv[4]); output << std::setprecision(17);
    if (!input || !output) return 3;
    auto nav=std::make_unique<nav_t>();
    for(int j=0;j<8;++j) nav->ion_gps[j]=ion.get<double>(std::string("boost_serialization.GNSS-SDR_iono_model.")+ion_names[j]);
    sol_t sol{};
    size_t index=0, calls=0;
    double record[4][7];
    while(input.read(reinterpret_cast<char*>(record),sizeof(record))) {
        const size_t current=index++;
        bool valid=true;
        for(int ch=0;ch<4;++ch) {
            valid &= record[ch][6]==1 && record[ch][0]==record[0][0];
            for(double value:record[ch]) valid &= std::isfinite(value);
        }
        if (!valid) continue; // Same >3-input gate, four GPS-only channels.
        if(mode=="first" && record[0][0]!=14052.0) continue;
        if(mode!="sequential") sol=sol_t{};
        const double initial[3]={sol.rr[0],sol.rr[1],sol.rr[2]};
        obsd_t obs[4]{}; eph_t eph[4]{};
        for(int ch=0;ch<4;++ch) {
            const auto& d=record[ch]; const int prn=static_cast<int>(d[5]);
            const auto& e=gps.at(prn);
            if(e.SV_health!=0 || e.PRN!=unsigned(prn)) return 4;
            Gnss_Synchro s; s.System='G';s.Signal[0]='1';s.Signal[1]='C';s.PRN=prn;s.Channel_ID=ch;
            s.RX_time=d[0];s.interp_TOW_ms=d[1]*1000;
            s.Carrier_Doppler_hz=d[2];s.Carrier_phase_rads=d[3]*TWO_PI;
            s.Pseudorange_m=d[4];s.Flag_valid_pseudorange=true;
            // CN0/other upstream flags absent from dump; SNR masks are disabled.
            insert_obs_to_rtklib(obs[ch],s,e.WN,0,false);
            eph[ch]=eph_to_rtklib(e,false);
        }
        nav->eph=eph;nav->n=4;
        for(int i=0;i<MAXSAT;++i)for(int j=0;j<NFREQ;++j) nav->lam[i][j]=satwavelen(i+1,j,nav.get());
        auto ssat=std::make_unique<ssat_t[]>(MAXSAT);
        char msg[256]{};
        const bool detail=record[0][0]==14052.0;
        FLAGS_v=detail?4:0;
        if(detail) std::cout << "RECONSTRUCTION_BEGIN tow=" << record[0][0]
            << " initial_ecef=" << initial[0] << ',' << initial[1] << ',' << initial[2]
            << " initial_estpos_clock_m=0 mask_deg=" << mask << " mode=" << mode << '\n' << std::flush;
        const int result=pntpos(obs,4,nav.get(),&opt,&sol,nullptr,ssat.get(),msg);
        ++calls;
        bool final_mask_ok=result!=0; int used=0; double rms=0, max_res=0;
        double azels[8]{};
        for(int ch=0;ch<4;++ch) {
            const auto& sat=ssat[obs[ch].sat-1];
            if(sat.vs) {
                final_mask_ok &= sat.azel[1]>=opt.elmin;
                azels[used*2]=sat.azel[0];azels[used*2+1]=sat.azel[1];
                ++used;rms+=sat.resp[0]*sat.resp[0];max_res=std::max(max_res,std::abs(sat.resp[0]));
            }
        }
        double dop[4]{}, llh[3]{};
        if(result){dops(used,azels,opt.elmin,dop);ecef2pos(sol.rr,llh);}
        output << "{\"index\":" << current << ",\"tow\":" << record[0][0]
            << ",\"result\":" << result << ",\"status\":" << int(sol.stat)
            << ",\"reason\":" << std::quoted(std::string(msg))
            << ",\"initial_ecef\":[" << initial[0] << ',' << initial[1] << ',' << initial[2]
            << "],\"mask_deg\":" << mask << ",\"final_mask_ok\":" << (final_mask_ok?"true":"false")
            << ",\"satellites_used\":" << used << ",\"satellites\":[";
        for(int ch=0;ch<4;++ch) {
            const auto& sat=ssat[obs[ch].sat-1];
            if(ch)output << ',';
            output << "{\"prn\":" << int(obs[ch].sat) << ",\"used\":" << (sat.vs?"true":"false")
                << ",\"elevation_deg\":" << sat.azel[1]*R2D
                << ",\"passes_mask\":" << (sat.azel[1]>=opt.elmin?"true":"false")
                << ",\"residual_m\":";
            if(sat.vs)output << sat.resp[0];else output << "null";
            output << '}';
        }
        output << "],\"position\":";
        if(result) output << "{\"ecef\":[" << sol.rr[0] << ',' << sol.rr[1] << ',' << sol.rr[2]
            << "],\"latitude_deg\":" << llh[0]*R2D << ",\"longitude_deg\":" << llh[1]*R2D
            << ",\"height_m\":" << llh[2] << ",\"clock_bias_s\":" << sol.dtr[0]
            << ",\"gdop\":" << dop[0] << ",\"residual_rms_m\":" << sqrt(rms/used)
            << ",\"max_abs_residual_m\":" << max_res << '}';
        else output << "null";
        output << "}\n";
        if(detail)std::cout << "RECONSTRUCTION_END result=" << result << " reason=" << msg
            << " used=" << used << " final_mask_ok=" << final_mask_ok << '\n' << std::flush;
        if(mode=="first")break;
    }
    std::cout << "RECONSTRUCTION_CALLS=" << calls << '\n';
    return calls?0:5;
}
