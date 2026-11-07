#include "presets.h"
#include <cstdio>
#include <fstream>
#include <stdexcept>
using namespace neutral;
static void require(bool good,const char* why) {if (!good) throw std::runtime_error(why);}
static void refused(const std::string& text) {bool bad=false;try {parse_preset(text);}catch(const std::invalid_argument&) {bad=true;}require(bad,"invalid preset accepted");}
int main(int argc,char** argv) {try {
    auto p=default_parameters();p[0]=-12;p[6]=1.123456789012345;
    const auto text=preset_json(p);require(parse_preset(text)==p,"roundtrip lost precision");
    auto invalid=text;invalid.insert(invalid.find('{')+1,"\"schema\":1,");refused(invalid);
    invalid=text;const auto where=invalid.find("\"length\"");invalid.insert(where,"\"length\":1,");refused(invalid);
    invalid=text;auto start=invalid.find("kliff-connected-v04");invalid.replace(start,19,"wrong-body");refused(invalid);
    refused("{}");refused(text+" garbage");refused(std::string(32769,' '));
    for (const char* value:{"true","null","\"1.0\"","1e999","999","[]"}) {
        invalid=text;start=invalid.find(':',invalid.find("\"length\""))+1;auto end=invalid.find(',',start);
        if (end==std::string::npos) end=invalid.find('}',start);invalid.replace(start,end-start,value);refused(invalid);
    }
    const auto dir=std::filesystem::current_path()/"preset-test-output";std::filesystem::create_directories(dir);
    const auto file=dir/"fit.json";save_preset_atomic(file,p);require(load_preset(file)==p,"disk roundtrip failed");
    p[0]=14;save_preset_atomic(file,p);require(load_preset(file)==p,"atomic replacement failed");
    // A rejected edit must not damage the previous valid file.
    auto bad=p;bad[0]=999;bool caught=false;try {save_preset_atomic(file,bad);}catch(const std::invalid_argument&) {caught=true;}
    require(caught && load_preset(file)==p,"rejected save damaged previous preset");
    caught=false;try {save_preset_atomic(dir,p);}catch (const std::system_error&) {caught=true;}
    require(caught && std::filesystem::is_directory(dir) && load_preset(file)==p,"failed replacement damaged preset directory");
    for (auto& e:std::filesystem::directory_iterator(dir)) require(e.path().filename().string().find(".tmp-")==std::string::npos,"orphan temporary file");
    if (argc>1) {auto real=load_preset(argv[1]);require(parse_preset(preset_json(real))==real,"editor preset incompatible");}
    std::filesystem::remove(file);std::filesystem::remove(dir);
    std::puts("PASS: editor JSON interoperability, precision, strict schema/types/ranges, duplicate rejection and atomic replacement.");
    return 0;
}catch(const std::exception& e) {std::fprintf(stderr,"FAIL: %s\n",e.what());return 1;}}
