// Prepared idle test. --plan and --self-test never create a device connection.
#include <ADF4002.h>
#include <ConnectionRegistry.h>
#include <IConnection.h>
#include <Logger.h>
#include <VersionInfo.h>
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <csignal>
#include <cstdint>
#include <ctime>
#include <functional>
#include <iomanip>
#include <iostream>
#include <memory>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace {
using Mono = std::chrono::steady_clock;
constexpr int settleSeconds = 30, windowSeconds = 300, lastSlot = settleSeconds + windowSeconds;
volatile std::sig_atomic_t interrupted = 0;
bool logging = true;
bool logFailed = false;
std::mutex logMutex;
const auto processStart = Mono::now();
void onSignal(int) { interrupted = 1; }

std::string jsonString(const std::string& s)
{
    std::ostringstream out;
    out << '"';
    for (unsigned char c : s) {
        if (c == '"' || c == '\\') out << '\\' << c;
        else if (c == '\n') out << "\\n";
        else if (c == '\r') out << "\\r";
        else if (c == '\t') out << "\\t";
        else if (c < 32) out << "\\u" << std::hex << std::setw(4) << std::setfill('0') << unsigned(c) << std::dec;
        else out << c;
    }
    return out.str() + '"';
}
std::string hex(std::uint64_t n, int width = 6)
{
    std::ostringstream out;
    out << "0x" << std::hex << std::setfill('0') << std::setw(width) << n;
    return out.str();
}
std::string number(double n) { std::ostringstream out; out << std::setprecision(12) << n; return out.str(); }
void log(const std::string& event, const std::string& fields = "")
{
    if (!logging) return;
    const auto wall = std::chrono::system_clock::now();
    const auto t = std::chrono::system_clock::to_time_t(wall);
    std::tm utc{}; gmtime_r(&t, &utc);
    const auto us = std::chrono::duration_cast<std::chrono::microseconds>(wall.time_since_epoch()).count() % 1000000;
    std::ostringstream stamp;
    stamp << std::put_time(&utc, "%Y-%m-%dT%H:%M:%S") << '.' << std::setfill('0') << std::setw(6) << us << 'Z';
    std::lock_guard<std::mutex> lock(logMutex);
    std::cout << "{\"event\":" << jsonString(event) << ",\"utc\":" << jsonString(stamp.str())
              << ",\"process_monotonic_s\":" << number(std::chrono::duration<double>(Mono::now()-processStart).count())
              << fields << "}" << std::endl;
    if(!std::cout.good()) logFailed=true;
}

struct Configuration {
    std::array<std::uint32_t, 4> words{};
    std::array<unsigned char, 12> bytes{};
};
Configuration configuration()
{
    lime::ADF4002 adf;
    // SetDefaults calls CalculateRN; initialize its frequency inputs first.
    adf.txtFref = 10.0; adf.txtFvco = 30.72;
    adf.SetDefaults();
    int r = 0, n = 0;
    adf.SetFrefFvco(10.0, 30.72, r, n);
    if (r != 125 || n != 384) throw std::runtime_error("Unexpected divider calculation");
    adf.SetReferenceCounterLatch(0, 0, r);  // LDP=0, ABW=0.
    adf.SetNCounterLatch(0, n);
    adf.SetFunctionLatch(7, 7, 0, 0, 1);  // MUXOUT=001, active-high digital LD.
    adf.SetFunctionLatchRgr(1, 0, 0, 0, 0);
    adf.SetInitializationLatch(7, 7, 0, 0, 1);
    adf.SetInitializationLatchRgr(1, 0, 0, 0, 0);
    Configuration cfg;
    adf.GetConfig(cfg.bytes.data());
    for (int i = 0; i < 4; ++i)
        cfg.words[i] = (std::uint32_t(cfg.bytes[3*i]) << 16) |
                       (std::uint32_t(cfg.bytes[3*i+1]) << 8) | cfg.bytes[3*i+2];
    return cfg;
}
std::string configFields(const Configuration& cfg)
{
    std::string words = "[";
    for (int i=0; i<4; ++i) { if (i) words += ','; words += jsonString(hex(cfg.words[i])); }
    return ",\"fref_hz\":10000000,\"fvco_hz\":30720000,\"r\":125,\"n\":384,\"pfd_hz\":80000"
           ",\"muxout_initialization\":1,\"muxout_function\":1,\"ldp\":0,\"words\":" + words + ']';
}

struct Device {
    virtual ~Device() = default;
    virtual int readDAC(double& value) = 0;
    virtual int readStatus(std::uint32_t& word) = 0;
    virtual int program(const Configuration& cfg) = 0;
    virtual int baseline(unsigned code) = 0;
};
enum class WritePhase { None, ADF, DAC };
struct RealDevice : Device {
    struct Release { void operator()(lime::IConnection* p) const {
        if (p) { log("closing"); lime::ConnectionRegistry::freeConnection(p); log("closed"); }
    }};
    std::unique_ptr<lime::IConnection, Release> conn;
    WritePhase phase = WritePhase::None;
    Configuration approved;
    unsigned dacCode = 0;

    explicit RealDevice(const Configuration& cfg) : approved(cfg)
    {
        lime::registerLogHandler([](lime::LogLevel level, const char* msg) {
            log("library_log", ",\"level\":" + jsonString(lime::logLevelToName(level)) +
                ",\"message\":" + jsonString(msg ? msg : ""));
        });
        log("library", ",\"version\":" + jsonString(lime::GetLibraryVersion()));
        lime::ConnectionHandle hint;
        hint.module="FX3"; hint.serial="0009061C01502715"; hint.addr="1d50:6108";
        log("opening_once", ",\"untouched_prior_state_observed\":false,\"constructor_packets_captured\":false");
        conn.reset(lime::ConnectionRegistry::makeConnection(hint));
        if (!conn || !conn->IsOpen()) throw std::runtime_error("Open failed; no retry");
        log("opened");
        conn->SetDataLogCallback([this](bool tx, const unsigned char* p, unsigned len) { packet(tx,p,len); });
        const auto info=conn->GetDeviceInfo();
        log("identity_after_open", ",\"name\":"+jsonString(info.deviceName)+
            ",\"serial\":"+jsonString(hex(info.boardSerialNumber,16))+
            ",\"hardware\":"+jsonString(info.hardwareVersion)+",\"firmware\":"+jsonString(info.firmwareVersion)+
            ",\"gateware_version\":"+jsonString(info.gatewareVersion)+",\"gateware_revision\":"+jsonString(info.gatewareRevision));
        if (info.deviceName!="LimeSDR-USB" || info.boardSerialNumber!=0x0009061c01502715ULL ||
            info.hardwareVersion!="4" || info.firmwareVersion!="4" || info.protocolVersion!="1" ||
            info.gatewareVersion!="2" || info.gatewareRevision!="23")
            throw std::runtime_error("Identity differs from reviewed HW4/FW4/GW2.23; no programming");
    }
    void packet(bool tx, const unsigned char* p, unsigned len)
    {
        bool allowed=!tx;
        if (tx && len==64) {
            allowed=(p[0]==0x00 || p[0]==0x56 || p[0]==0x62);
            if (phase==WritePhase::ADF && p[0]==0x31 && p[2]==4 && p[3]==0)
                allowed=std::equal(approved.bytes.begin(),approved.bytes.end(),p+8);
            if (phase==WritePhase::DAC && p[0]==0x61 && p[2]==1 && p[3]==0)
                allowed=(p[8]==0 && p[9]==0 && p[10]==0 && p[11]==dacCode);
        }
        std::ostringstream bytes;
        for(unsigned i=0;i<len;++i) bytes<<std::hex<<std::setfill('0')<<std::setw(2)<<unsigned(p[i]);
        log("packet",",\"direction\":"+jsonString(tx?"TX":"RX")+",\"hex\":"+jsonString(bytes.str())+
            ",\"allowed\":"+(allowed?"true":"false"));
        if (!allowed) throw std::runtime_error("Unapproved protocol command blocked before Write");
    }
    int readDAC(double& value) override {
        const std::uint8_t id=0;
        return conn->CustomParameterRead(&id,&value,1,nullptr);
    }
    int readStatus(std::uint32_t& word) override { return conn->ReadRegister(0xc8,word); }
    int program(const Configuration& cfg) override {
        phase=WritePhase::ADF;
        try { const int rc=conn->TransactSPI(0x30,cfg.words.data(),nullptr,4); phase=WritePhase::None; return rc; }
        catch (...) { phase=WritePhase::None; throw; }
    }
    int baseline(unsigned code) override {
        const std::uint8_t id=0; const double value=code; dacCode=code; phase=WritePhase::DAC;
        try { const int rc=conn->CustomParameterWrite(&id,&value,1,""); phase=WritePhase::None; return rc; }
        catch (...) { phase=WritePhase::None; throw; }
    }
};

struct Clock {
    std::function<double()> now;
    std::function<void(double)> until;
};
struct Sample { int slot, rc; std::uint32_t raw; double request, completion; };
struct Results {
    bool attempted=false, programmed=false, stopped=false, baselineAttempted=false, baselineOK=false;
    int baselineCode=-1, programRC=-999, baselineRC=-999;
    std::vector<Sample> samples;
    std::vector<int> missing;
    std::string error;
};

Results test(Device& device, const Configuration& cfg, const Clock& clock)
{
    Results out;
    try {
        double dac=-1; const int drc=device.readDAC(dac);
        log("baseline_code_before_program",",\"status\":"+std::to_string(drc)+",\"reported_code\":"+
            (drc==0 && std::isfinite(dac)?number(dac):"null")+",\"previous_control_mode_known\":false");
        if (drc || !std::isfinite(dac) || dac<0 || dac>255 || dac!=std::floor(dac))
            throw std::runtime_error("No valid reviewed 8-bit DAC baseline code; no ADF programming");
        out.baselineCode=int(dac);
        std::uint32_t prior=0; const int prc=device.readStatus(prior);
        log("raw_before_program_after_open",",\"status\":"+std::to_string(prc)+",\"raw\":"+
            (prc==0?jsonString(hex(prior,4)):"null")+",\"interpretation\":\"unknown MUXOUT configuration\"");
        if (prc) throw std::runtime_error("Initial status read failed; no programming");
        if (interrupted) throw std::runtime_error("Interrupted before programming");
        log("program_intent",configFields(cfg));
        if (!std::cout.good()) throw std::runtime_error("Logging failed before programming");
        out.attempted=true; out.programRC=device.program(cfg);
        log("program_result",",\"status\":"+std::to_string(out.programRC)+",\"latch_readback_available\":false");
        if (out.programRC) throw std::runtime_error("Programming failed or uncertain; return to DAC baseline");
        if (logFailed) throw std::runtime_error("Programming log write failed; return to DAC baseline");
        out.programmed=true;
        const double epoch=clock.now();
        log("sampling_epoch",",\"settling_s\":30,\"window_s\":300,\"interval_s\":1,\"expected_window_samples\":301");
        int slot=0;
        while(slot<=lastSlot && !interrupted) {
            clock.until(epoch+slot);
            if(interrupted) break;
            const double ready=clock.now()-epoch;
            // Skip expired slots instead of manufacturing catch-up observations.
            const int current=std::max(slot,int(std::floor(ready+1e-7)));
            for(;slot<std::min(current,lastSlot+1);++slot) {
                out.missing.push_back(slot);
                log("missing_slot",",\"slot\":"+std::to_string(slot)+",\"scheduled_s\":"+std::to_string(slot));
            }
            if(slot>lastSlot) break;
            Sample s{slot,-1,0,clock.now()-epoch,0};
            s.rc=device.readStatus(s.raw); s.completion=clock.now()-epoch;
            out.samples.push_back(s);
            log("sample",",\"phase\":"+jsonString(slot<settleSeconds?"settling":"five_minute_window")+
                ",\"slot\":"+std::to_string(slot)+",\"scheduled_s\":"+std::to_string(slot)+
                ",\"request_s\":"+number(s.request)+",\"completion_s\":"+number(s.completion)+
                ",\"lateness_s\":"+number(s.request-slot)+",\"status\":"+std::to_string(s.rc)+
                ",\"raw\":"+(s.rc==0?jsonString(hex(s.raw,4)):"null")+
                ",\"lock_sample\":"+(s.rc==0?std::to_string((s.raw>>1)&1):"null"));
            if(logFailed) throw std::runtime_error("Observation log write failed; return to DAC baseline");
            ++slot;
        }
        out.stopped=interrupted;
        // Report the unobserved remaining slots on an ordinary interruption.
        for(;slot<=lastSlot;++slot) {
            out.missing.push_back(slot);
            log("missing_slot",",\"slot\":"+std::to_string(slot)+",\"reason\":\"interrupted\"");
        }
    } catch(const std::exception& e) {
        out.error=e.what(); log("test_error",",\"message\":"+jsonString(out.error));
    }
    out.stopped=interrupted!=0;
    if(out.programmed) {
        // Exceptions can exit the sampling loop before its normal gap handling.
        for(int slot=0;slot<=lastSlot;++slot) {
            const bool sampled=std::any_of(out.samples.begin(),out.samples.end(),[&](const Sample& s){return s.slot==slot;});
            if(!sampled && std::find(out.missing.begin(),out.missing.end(),slot)==out.missing.end()) {
                out.missing.push_back(slot);
                log("missing_slot",",\"slot\":"+std::to_string(slot)+",\"reason\":\"test_aborted\"");
            }
        }
    }
    // Same connection, one baseline attempt even after uncertain ADF programming.
    if(out.attempted) {
        out.baselineAttempted=true;
        try {
            log("baseline_intent",",\"parameter_id\":0,\"code\":"+std::to_string(out.baselineCode)+
                ",\"mode\":\"DAC control; ADF CP three-state and MUXOUT DGND\",\"exact_prior_state_restoration\":false");
            out.baselineRC=device.baseline(unsigned(out.baselineCode));
            log("baseline_write_result",",\"status\":"+std::to_string(out.baselineRC));
            if(out.baselineRC==0) {
                clock.until(clock.now()+1.0);
                double readback=-1; std::uint32_t raw=0;
                const int drc=device.readDAC(readback), src=device.readStatus(raw);
                out.baselineOK=(drc==0 && readback==out.baselineCode && src==0 && (raw&2)==0);
                log("baseline_check",",\"dac_read_status\":"+std::to_string(drc)+",\"reported_code\":"+
                    (drc==0 && std::isfinite(readback)?number(readback):"null")+",\"raw_status_read_rc\":"+std::to_string(src)+
                    ",\"raw\":"+(src==0?jsonString(hex(raw,4)):"null")+",\"consistent_with_documented_baseline\":"+
                    (out.baselineOK?"true":"false")+",\"oscillator_frequency_verified\":false");
            }
        } catch(const std::exception& e) {
            log("baseline_error",",\"message\":"+jsonString(e.what()));
        }
        if(!out.baselineOK) log("final_state_unknown",",\"retry_or_reconnect\":false");
    }
    return out;
}

struct Metrics {
    int mainSamples=0, mainErrors=0, mainLow=0, mainMissing=0, late=0, spacingGaps=0, transitions=0;
    double firstHigh=-1, threeHigh=-1;
};
Metrics metrics(const Results& r)
{
    Metrics m; int streak=0, previousSlot=-2, previousBit=-1; double previousCompletion=-1;
    for(int slot:r.missing) if(slot>=settleSeconds) ++m.mainMissing;
    for(const auto& s:r.samples) {
        const int bit=s.rc==0?int((s.raw>>1)&1):-1;
        const bool adjacent=s.slot==previousSlot+1;
        const bool timely=previousCompletion<0 || s.completion-previousCompletion<=1.5;
        if(s.request-s.slot>0.25) ++m.late;
        if(previousCompletion>=0 && !timely) ++m.spacingGaps;
        if(bit==1) {
            if(m.firstHigh<0) m.firstHigh=s.completion;
            if(adjacent && timely && previousBit==0) ++m.transitions;
            streak=adjacent && timely?streak+1:1;
            if(streak>=3 && m.threeHigh<0) m.threeHigh=s.completion;
        } else streak=0;
        if(s.slot>=settleSeconds) {
            ++m.mainSamples;
            if(s.rc) ++m.mainErrors;
            else if(bit==0) ++m.mainLow;
        }
        previousSlot=s.slot; previousBit=bit; previousCompletion=s.completion;
    }
    return m;
}
void summary(const Results& r)
{
    const auto m=metrics(r);
    log("summary",",\"program_attempted\":"+std::string(r.attempted?"true":"false")+
        ",\"window_started\":"+(r.programmed?"true":"false")+",\"error\":"+jsonString(r.error)+
        ",\"all_scheduled_window_samples_high\":"+
        (r.programmed && m.mainSamples==301 && !m.mainErrors && !m.mainMissing && !m.mainLow?"true":"false")+
        ",\"program_status\":"+std::to_string(r.programRC)+",\"expected_window_samples\":301,\"window_samples\":"+
        std::to_string(m.mainSamples)+",\"window_read_errors\":"+std::to_string(m.mainErrors)+
        ",\"window_unlocked_samples\":"+std::to_string(m.mainLow)+",\"window_missing_slots\":"+std::to_string(m.mainMissing)+
        ",\"late_requests_over_250ms_all_phases\":"+std::to_string(m.late)+",\"completion_gaps_over_1_5s_all_phases\":"+
        std::to_string(m.spacingGaps)+",\"observed_low_to_high_transitions\":"+std::to_string(m.transitions)+
        ",\"first_high_after_program_s\":"+(m.firstHigh<0?"null":number(m.firstHigh))+
        ",\"first_three_consecutive_high_confirmed_s\":"+(m.threeHigh<0?"null":number(m.threeHigh))+
        ",\"interrupted\":"+(r.stopped?"true":"false")+",\"baseline_attempted\":"+(r.baselineAttempted?"true":"false")+
        ",\"baseline_consistent\":"+(r.baselineOK?"true":"false")+
        ",\"continuous_lock_between_samples_proven\":false,\"receiver_streaming_tested\":false");
}

struct FakeDevice : Device {
    double& time; int writes=0, returns=0, reads=0;
    bool failProgram=false, failBaseline=false, faults=false, throwing=false, failDAC=false, stop=false, failInitialStatus=false, failLog=false;
    explicit FakeDevice(double& t):time(t){}
    int readDAC(double& v) override { v=125; return failDAC?-1:0; }
    int readStatus(std::uint32_t& raw) override {
        ++reads;
        if(failInitialStatus && !writes) return -1;
        if(throwing && writes && !returns) throw std::runtime_error("simulated read exception");
        if(returns) { raw=0; return 0; }
        int slot=int(std::floor(time+1e-7));
        if(stop && writes && slot==4) interrupted=1;
        if(failLog && writes && slot==2) logFailed=true;
        raw=slot>=1 && slot!=100?2:0;
        if(faults && writes && slot==50) time+=3.2;
        return faults && writes && slot==31?-1:0;
    }
    int program(const Configuration&) override { ++writes; return failProgram?-1:0; }
    int baseline(unsigned code) override { if(code!=125) throw std::runtime_error("bad baseline code"); ++returns; return failBaseline?-1:0; }
};
void require(bool b,const char* text) { if(!b) throw std::runtime_error(text); }
void selfTest(const Configuration& cfg)
{
    logging=false;
    require(cfg.words==std::array<std::uint32_t,4>{0x1f8093,0x1f8092,0x0001f4,0x018001},"Unexpected installed-library latch words");
    for(int scenario=0;scenario<9;++scenario) {
        interrupted=0; logFailed=false;
        double time=0; FakeDevice d(time);
        d.faults=scenario==1; d.failProgram=scenario==2; d.failBaseline=scenario==3;
        d.throwing=scenario==4; d.failDAC=scenario==5;
        d.stop=scenario==6; d.failInitialStatus=scenario==7;
        d.failLog=scenario==8;
        Clock c{[&](){return time;},[&](double target){time=std::max(time,target);}};
        const auto r=test(d,cfg,c); const auto m=metrics(r);
        require(d.writes==(scenario==5 || scenario==7?0:1),"Unexpected program count");
        require(d.returns==(scenario==5 || scenario==7?0:1),"Baseline omitted or retried");
        if(scenario==0) require(m.mainSamples==301 && m.mainLow==1 && m.mainErrors==0 && m.mainMissing==0 && m.firstHigh==1 && m.threeHigh==3 && r.baselineOK,"Clean sampling/acquisition accounting failed");
        if(scenario==1) require(m.mainSamples==299 && m.mainLow==1 && m.mainErrors==1 && m.mainMissing==2 && m.spacingGaps>0 && r.baselineOK,"Error/gap accounting failed");
        if(scenario==2 || scenario==4) require(r.samples.empty() && r.baselineOK,"Uncertain-program/exception cleanup failed");
        if(scenario==3) require(!r.baselineOK,"Failed baseline reported as restored");
        if(scenario==5) require(!r.attempted && !r.baselineAttempted,"Bad initial DAC read permitted programming");
        if(scenario==6) require(r.stopped && m.mainMissing==301 && r.baselineOK,"Interrupt did not return to baseline and record missing window");
        if(scenario==7) require(!r.attempted && !r.baselineAttempted,"Bad initial status permitted programming");
        if(scenario==8) require(r.samples.size()==3 && !r.error.empty() && r.baselineOK && m.mainMissing==301,"Log failure did not abort observations and return baseline");
    }
    interrupted=0; logFailed=false;
    logging=true;
    log("self_test_passed",",\"hardware_connections\":0,\"scenarios\":9");
}
} // namespace

int main(int argc,char** argv)
{
    try {
        const auto cfg=configuration();
        const std::string mode=argc==2?argv[1]:"--plan";
        if(argc>2) throw std::runtime_error("Unexpected arguments");
        if(mode=="--self-test") { selfTest(cfg); return 0; }
        if(mode=="--plan") {
            log("plan",configFields(cfg)+",\"settling_s\":30,\"sampling_window_s\":300,\"interval_s\":1,\"window_samples\":301,\"baseline\":\"save reported 8-bit DAC code; return to DAC control, not unknown prior ADF state\",\"hardware_connections\":0");
            return 0;
        }
        if(mode!="--execute-approved-idle-test") throw std::runtime_error("Unsupported mode; no connection");
        std::signal(SIGINT,onSignal); std::signal(SIGTERM,onSignal);
        RealDevice device(cfg);
        Clock clock{[](){return std::chrono::duration<double>(Mono::now().time_since_epoch()).count();},
                    [](double target){while(!interrupted) {const double now=std::chrono::duration<double>(Mono::now().time_since_epoch()).count(); if(now>=target) break; std::this_thread::sleep_for(std::chrono::duration<double>(std::min(0.1,target-now)));}}};
        const auto result=test(device,cfg,clock); summary(result);
        if(!result.programmed || !result.baselineOK || !result.error.empty() || result.stopped) return 3;
        const auto m=metrics(result);
        return m.mainSamples==301 && m.mainErrors==0 && m.mainMissing==0 && m.mainLow==0 && m.late==0 && m.spacingGaps==0?0:4;
    } catch(const std::exception& e) {
        log("fatal",",\"message\":"+jsonString(e.what())); return 2;
    }
}
