// One low-level FX3 connection. No RFIC initialization, setters or streaming.
// Must be launched through run_lime_reference_once.py after host ownership checks.
#include <ConnectionRegistry.h>
#include <IConnection.h>
#include <Logger.h>
#include <VersionInfo.h>
#include <chrono>
#include <cstdint>
#include <ctime>
#include <iomanip>
#include <iostream>
#include <memory>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <string>

namespace {
std::mutex outputMutex;
const auto started = std::chrono::steady_clock::now();

std::string quoted(const std::string& value)
{
    std::ostringstream out;
    out << '"';
    for (unsigned char c : value) {
        switch (c) {
        case '"': out << "\\\""; break;
        case '\\': out << "\\\\"; break;
        case '\n': out << "\\n"; break;
        case '\r': out << "\\r"; break;
        case '\t': out << "\\t"; break;
        default:
            if (c < 0x20) out << "\\u" << std::hex << std::setw(4) << std::setfill('0') << unsigned(c) << std::dec;
            else out << char(c);
        }
    }
    return out.str() + '"';
}

std::string hexValue(std::uint64_t value, int width = 4)
{
    std::ostringstream out;
    out << "0x" << std::hex << std::setw(width) << std::setfill('0') << value;
    return out.str();
}

void record(const std::string& event, const std::string& fields = "")
{
    const auto now = std::chrono::system_clock::now();
    const auto stamp = std::chrono::system_clock::to_time_t(now);
    std::tm utc{};
    gmtime_r(&stamp, &utc);
    std::ostringstream time;
    time << std::put_time(&utc, "%Y-%m-%dT%H:%M:%SZ");
    const double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count();
    std::lock_guard<std::mutex> lock(outputMutex);
    std::cout << "{\"utc\":" << quoted(time.str()) << ",\"elapsed_s\":" << elapsed
              << ",\"event\":" << quoted(event) << fields << "}" << std::endl;
}

void libraryLog(lime::LogLevel level, const char* message)
{
    record("library_log", ",\"level\":" + quoted(lime::logLevelToName(level)) +
           ",\"message\":" + quoted(message ? message : ""));
}

void packetLog(bool tx, const unsigned char* data, unsigned length)
{
    std::ostringstream bytes;
    for (unsigned i = 0; i < length; ++i)
        bytes << std::hex << std::setw(2) << std::setfill('0') << unsigned(data[i]);
    const bool allowed = !tx || (length && (data[0] == 0x00 || data[0] == 0x56));
    record("packet_after_open", ",\"direction\":" + quoted(tx ? "TX" : "RX") +
           ",\"hex\":" + quoted(bytes.str()) + ",\"allowed\":" + (allowed ? "true" : "false"));
    // The installed callback executes before Write(). Block any unexpected
    // post-constructor command before it could reach hardware.
    if (!allowed) throw std::runtime_error("Unexpected non-read protocol command blocked before Write");
}

struct CloseConnection {
    void operator()(lime::IConnection* conn) const
    {
        if (!conn) return;
        record("closing");
        lime::ConnectionRegistry::freeConnection(conn);
        record("closed", ",\"method\":\"freeConnection / FX3 Close\"");
    }
};
}  // namespace

int main(int argc, char** argv)
{
    if (argc != 2 || std::string(argv[1]) != "--run-authorized-once") {
        std::cerr << "Use the ownership-checking Python launcher; no device opened.\n";
        return 2;
    }
    lime::registerLogHandler(libraryLog);
    record("library", ",\"version\":" + quoted(lime::GetLibraryVersion()) +
           ",\"abi\":" + quoted(lime::GetABIVersion()));
    try {
        lime::ConnectionHandle hint;
        hint.module = "FX3";
        hint.serial = "0009061C01502715";
        hint.addr = "1d50:6108";
        record("opening_once", ",\"hint\":" + quoted(hint.serialize()) +
               ",\"untouched_prior_state_observed\":false");
        std::unique_ptr<lime::IConnection, CloseConnection> conn(
            lime::ConnectionRegistry::makeConnection(hint));  // Exactly one factory call; no retry.
        if (!conn || !conn->IsOpen()) {
            record("open_failed", ",\"retry\":false");
            return 3;
        }
        record("opened", ",\"constructor_packets_captured\":false");
        conn->SetDataLogCallback(packetLog);  // In-memory observer, no device setting.
        const auto info = conn->GetDeviceInfo();
        record("identity_after_open",
               ",\"device_name\":" + quoted(info.deviceName) +
               ",\"hardware_version\":" + quoted(info.hardwareVersion) +
               ",\"firmware_version\":" + quoted(info.firmwareVersion) +
               ",\"protocol_version\":" + quoted(info.protocolVersion) +
               ",\"gateware_version\":" + quoted(info.gatewareVersion) +
               ",\"gateware_revision\":" + quoted(info.gatewareRevision) +
               ",\"gateware_target\":" + quoted(info.gatewareTargetBoard) +
               ",\"board_serial_hex\":" + quoted(hexValue(info.boardSerialNumber, 16)));
        if (info.deviceName != "LimeSDR-USB" || info.boardSerialNumber != 0x0009061C01502715ULL) {
            record("identity_mismatch", ",\"further_reads_aborted\":true");
            return 4;
        }
        int errors = 0;
        // Read only the identity registers and raw peripheral input. No ADF
        // latch readback is possible; the bit deliberately has no lock label.
        for (std::uint32_t addr : {0x0000U, 0x0001U, 0x0002U, 0x0003U, 0x00c8U}) {
            std::uint32_t word = 0;
            const int status = conn->ReadRegister(addr, word);
            std::string fields = ",\"address\":" + quoted(hexValue(addr)) +
                ",\"status\":" + std::to_string(status) + ",\"raw\":";
            fields += status == 0 ? quoted(hexValue(word)) : "null";
            if (addr == 0xc8) {
                fields += ",\"bit1_raw\":" + (status == 0 ? std::to_string((word >> 1) & 1) : "null");
                fields += ",\"interpretation\":\"inconclusive; gateware map and MUXOUT configuration require separate evidence\"";
            }
            record("register_after_open", fields);
            if (status != 0) ++errors;
        }
        conn.reset();
        record("complete", ",\"register_read_errors\":" + std::to_string(errors) +
               ",\"capture_started\":false,\"explicit_settings_changed\":false");
        return errors ? 5 : 0;
    } catch (const std::exception& error) {
        record("exception", ",\"message\":" + quoted(error.what()) + ",\"retry\":false");
        return 6;
    }
}
