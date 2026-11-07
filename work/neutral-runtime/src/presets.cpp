#include "presets.h"
#include <Windows.h>
#include <nlohmann/json.hpp>
#include <atomic>
#include <fstream>
#include <stdexcept>
#include <system_error>
#include <unordered_set>

namespace neutral {
using Json=nlohmann::json;
std::string preset_json(const Parameters& parameters) {
    if (!valid_parameters(parameters)) throw std::invalid_argument("Invalid fitting parameters.");
    Json values=Json::object();
    for (unsigned i=0;i<control_count;++i) values[control_specs()[i].key]=parameters[i];
    return Json{{"schema",1},{"asset","kliff-connected-v04"},{"parameters",values}}.dump(2)+"\n";
}
Parameters parse_preset(std::string_view text) {
    if (text.empty() || text.size()>32768) throw std::invalid_argument("Preset must contain at most 32 KiB.");
    std::vector<std::unordered_set<std::string>> keys;
    auto callback=[&](int depth,Json::parse_event_t event,Json& value) {
        if (depth>8 || event==Json::parse_event_t::array_start) throw std::invalid_argument("Unsupported preset structure.");
        if (event==Json::parse_event_t::object_start) keys.emplace_back();
        if (event==Json::parse_event_t::key && (keys.empty() || !keys.back().insert(value.get<std::string>()).second))
            throw std::invalid_argument("Duplicate preset key.");
        if (event==Json::parse_event_t::object_end) keys.pop_back();
        return true;
    };
    Json j;
    try {j=Json::parse(text.begin(),text.end(),callback);}
    catch (const Json::exception&) {throw std::invalid_argument("Invalid preset JSON.");}
    if (!j.is_object() || j.size()!=3 || !j.contains("schema") || !j["schema"].is_number_integer() ||
        j["schema"]!=1 || !j.contains("asset") || j["asset"]!="kliff-connected-v04" ||
        !j.contains("parameters") || !j["parameters"].is_object() || j["parameters"].size()!=control_count)
        throw std::invalid_argument("Preset schema or body asset does not match.");
    Parameters result{};const auto& values=j["parameters"];
    for (unsigned i=0;i<control_count;++i) {
        const auto key=control_specs()[i].key;
        if (!values.contains(key) || !values[key].is_number()) throw std::invalid_argument("Preset has missing or nonnumeric controls.");
        result[i]=values[key].get<double>();
    }
    if (!valid_parameters(result)) throw std::invalid_argument("Preset contains unsupported control values.");
    return result;
}
Parameters load_preset(const std::filesystem::path& path) {
    std::ifstream f(path,std::ios::binary|std::ios::ate);
    if (!f) throw std::runtime_error("Cannot open preset.");
    const auto n=f.tellg();if (n<=0 || n>32768) throw std::invalid_argument("Preset must contain at most 32 KiB.");
    std::string bytes(static_cast<size_t>(n),'\0');f.seekg(0);
    if (!f.read(bytes.data(),n)) throw std::runtime_error("Cannot read preset.");
    return parse_preset(bytes);
}
void save_preset_atomic(const std::filesystem::path& path,const Parameters& parameters) {
    const auto bytes=preset_json(parameters);
    if (path.empty() || path.filename().empty()) throw std::invalid_argument("Choose a preset filename.");
    const auto target=std::filesystem::absolute(path);
    static std::atomic<unsigned long long> serial{};
    std::filesystem::path temporary;HANDLE file=INVALID_HANDLE_VALUE;
    for (int attempt=0;attempt<16;++attempt) {
        temporary=target;temporary+=L".tmp-"+std::to_wstring(GetCurrentProcessId())+L"-"+std::to_wstring(GetTickCount64())+L"-"+std::to_wstring(++serial);
        file=CreateFileW(temporary.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);
        if (file!=INVALID_HANDLE_VALUE) break;
        if (GetLastError()!=ERROR_FILE_EXISTS && GetLastError()!=ERROR_ALREADY_EXISTS)
            throw std::system_error(GetLastError(),std::system_category(),"Cannot create temporary preset");
    }
    if (file==INVALID_HANDLE_VALUE) throw std::runtime_error("Cannot reserve temporary preset filename.");
    DWORD count{};
    const bool written=WriteFile(file,bytes.data(),static_cast<DWORD>(bytes.size()),&count,nullptr) && count==bytes.size();
    const bool flushed=written && FlushFileBuffers(file);
    const auto error=GetLastError();const bool closed=CloseHandle(file);
    if (!written || !flushed || !closed) {
        DeleteFileW(temporary.c_str());throw std::system_error(error?error:ERROR_WRITE_FAULT,std::system_category(),"Cannot write preset");
    }
    if (!MoveFileExW(temporary.c_str(),target.c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)) {
        const auto reason=GetLastError();DeleteFileW(temporary.c_str());
        throw std::system_error(reason,std::system_category(),"Cannot replace preset");
    }
}
}
