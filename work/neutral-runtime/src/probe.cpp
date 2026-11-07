// Opt-in upload observation for the neutral runtime binding. No pose/vertex writes.
#include <Windows.h>
#include <MinHook.h>
#include "probe_context.h"
#include "upload_profiles.h"
#include <atomic>
#include <cstdio>
#include <cstring>
#include <cwchar>
#include <cstdint>
using U=std::uint64_t;
extern "C" {void* gProbeOriginal=nullptr;}
HMODULE self{};wchar_t directory[MAX_PATH]{};
std::atomic<bool> capture{false};std::atomic<U> deadline{},next_sample{};
SRWLOCK rows_lock=SRWLOCK_INIT,log_lock=SRWLOCK_INIT;
struct EntrySample {U at{},field_a8{},field_b8{},field90{},indirect{};unsigned char header[256]{},a8_header[256]{},b8_header[256]{},field90_header[192]{},indirect_header[192]{};unsigned reads{};};
struct Row {U tick{},thread{},register_args[4]{},stack[10]{},vector{},count{},entries[6]{},sample_start{};unsigned char object[512]{};EntrySample samples[6]{};bool object_read{},vector_read{};};
Row rows[64]{};unsigned queued{},written{};void* target{};std::atomic<bool> hooked{};
void log(const char* text){AcquireSRWLockExclusive(&log_lock);wchar_t p[MAX_PATH];swprintf_s(p,L"%sNeutralRuntimeProbe.log",directory);FILE* f{};if(!_wfopen_s(&f,p,L"ab")&&f){std::fprintf(f,"[%llu] %s\r\n",GetTickCount64(),text);std::fclose(f);}ReleaseSRWLockExclusive(&log_lock);}
bool copy(U address,void* destination,size_t bytes){
 if(address<0x10000||bytes>4096||address>0x7fffffffffff-bytes)return false;
 MEMORY_BASIC_INFORMATION m{};if(!VirtualQuery(reinterpret_cast<void*>(address),&m,sizeof(m))||m.State!=MEM_COMMIT||m.Protect&(PAGE_NOACCESS|PAGE_GUARD)||address+bytes>reinterpret_cast<U>(m.BaseAddress)+m.RegionSize)return false;
 __try{std::memcpy(destination,reinterpret_cast<void*>(address),bytes);return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
extern "C" void ProbeCapture(const CpuContext* cpu){
 const DWORD error=GetLastError();
 if(!capture.load(std::memory_order_relaxed)){SetLastError(error);return;}
 U now=GetTickCount64(),expected=next_sample.load(std::memory_order_relaxed);
 if(now>deadline.load(std::memory_order_relaxed)){capture=false;SetLastError(error);return;}
 if(now<expected||!next_sample.compare_exchange_strong(expected,now+300)){SetLastError(error);return;}
 if(!TryAcquireSRWLockExclusive(&rows_lock)){SetLastError(error);return;}
 if(queued<64){
  auto& r=rows[queued++];r.tick=now;r.thread=GetCurrentThreadId();r.register_args[0]=cpu->gpr[1];r.register_args[1]=cpu->gpr[2];r.register_args[2]=cpu->gpr[8];r.register_args[3]=cpu->gpr[9];
  copy(cpu->gpr[4]+8,r.stack,sizeof(r.stack));
  r.object_read=copy(cpu->gpr[2],r.object,sizeof(r.object));
  if(r.object_read){std::memcpy(&r.vector,r.object+0x70,8);std::uint32_t n{};std::memcpy(&n,r.object+0x78,4);r.count=n;
   r.sample_start=((queued-1)*6)%((n>0)?n:1);
   const auto take=n-r.sample_start<6?n-r.sample_start:6;
   if(n>0&&n<=2048&&copy(r.vector+r.sample_start*8,r.entries,sizeof(U)*take)){
    r.vector_read=true;
    for(unsigned i=0;i<take;++i){
     auto& s=r.samples[i];s.at=r.entries[i];
     if(copy(s.at,s.header,sizeof(s.header))){
      s.reads|=1;std::memcpy(&s.field_a8,s.header+0xa8,8);std::memcpy(&s.field_b8,s.header+0xb8,8);
      if(copy(s.field_b8,s.b8_header,sizeof(s.b8_header)))s.reads|=2;
      if(copy(s.field_a8,s.a8_header,sizeof(s.a8_header))){
       s.reads|=4;std::memcpy(&s.field90,s.a8_header+0x90,8);
       if(copy(s.field90,s.field90_header,sizeof(s.field90_header))){
        s.reads|=8;std::memcpy(&s.indirect,s.field90_header,8);
        if(copy(s.indirect,s.indirect_header,sizeof(s.indirect_header)))s.reads|=16;
       }
      }
     }
    }
   }}
 }
 if(queued>=64)capture=false;
 ReleaseSRWLockExclusive(&rows_lock);SetLastError(error);
}
bool known_chain(void* start){
 U at=reinterpret_cast<U>(start);
 for(int n=0;n<5;++n){
  HMODULE owner{};wchar_t path[MAX_PATH]{};
  if(GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,reinterpret_cast<wchar_t*>(at),&owner)&&GetModuleFileNameW(owner,path,MAX_PATH)){
   wchar_t* name=wcsrchr(path,L'\\');if(name&&!_wcsicmp(name+1,L"BodyPhysics.asi"))return true;
  }
  unsigned char code[16]{};if(!copy(at,code,sizeof(code)))return false;
  if(code[0]==0xe9){std::int32_t delta{};std::memcpy(&delta,code+1,4);at=at+5+delta;continue;}
  if(code[0]==0xff&&code[1]==0x25){std::int32_t delta{};std::memcpy(&delta,code+2,4);U next{};if(!copy(at+6+delta,&next,8))return false;at=next;continue;}
  return false;
 }return false;
}
bool install(){
 auto base=reinterpret_cast<unsigned char*>(GetModuleHandleW(nullptr));auto dos=reinterpret_cast<IMAGE_DOS_HEADER*>(base);auto nt=reinterpret_cast<IMAGE_NT_HEADERS64*>(base+dos->e_lfanew);
 const auto profile=neutral::upload_profile(nt->FileHeader.TimeDateStamp,nt->OptionalHeader.SizeOfImage);
 if(!profile){log("Refused: executable fingerprint has no inspected upload profile.");return false;}
 target=base+profile->rva;
 unsigned char prefix[sizeof(neutral::upload_prefix)]{};
 if(!copy(reinterpret_cast<U>(target),prefix,sizeof(prefix))){log("Refused: unreadable upload entry.");return false;}
 const bool untouched=!std::memcmp(prefix,neutral::upload_prefix,sizeof(prefix));
 const bool chained=!std::memcmp(prefix+16,neutral::upload_prefix+16,sizeof(prefix)-16)&&known_chain(target);
 if(!untouched && !chained){log("Refused: upload prefix does not match the inspected profile or recognized detour chain.");return false;}
 if(MH_Initialize()!=MH_OK){log("Refused: private hook manager initialization failed.");return false;}
 if(MH_CreateHook(target,reinterpret_cast<void*>(&ProbeEntry),&gProbeOriginal)!=MH_OK){log("Refused: could not construct an upload trampoline.");return false;}
 if(MH_EnableHook(target)!=MH_OK){MH_RemoveHook(target);log("Refused: upload trampoline could not be enabled.");return false;}
 hooked=true;char message[256];std::snprintf(message,sizeof(message),"Upload observer installed at inspected RVA 0x%x (PE timestamp 0x%x, image size 0x%x). No pose/mesh values are changed.",profile->rva,profile->timestamp,profile->image_size);log(message);return true;
}
void hex(FILE* f,const unsigned char* data,size_t n){for(size_t i=0;i<n;++i)std::fprintf(f,"%02x",data[i]);}
void flush(){
 AcquireSRWLockExclusive(&rows_lock);
 if(written<queued){wchar_t p[MAX_PATH];swprintf_s(p,L"%sNeutralRuntimeProbe.capture.tsv",directory);FILE* f{};
  if(!_wfopen_s(&f,p,written?L"ab":L"wb")&&f){if(!written)std::fprintf(f,"tick\tthread\trcx\trdx\tr8\tr9\tshadow_and_stack_words\tRDX_header_read\tRDX_header_hex\tfield70_pointer\tfield78_u32\tarray_read\tsample_start\tentry_samples_v2\r\n");
   for(;written<queued;++written){auto& r=rows[written];std::fprintf(f,"%llu\t%llu\t%llx\t%llx\t%llx\t%llx\t",r.tick,r.thread,r.register_args[0],r.register_args[1],r.register_args[2],r.register_args[3]);for(auto v:r.stack)std::fprintf(f,"%llx,",v);std::fprintf(f,"\t%d\t",r.object_read);hex(f,r.object,sizeof(r.object));std::fprintf(f,"\t%llx\t%llu\t%d\t%llu\t",r.vector,r.count,r.vector_read,r.sample_start);
    for(auto& s:r.samples){std::fprintf(f,"%llx:%u:%llx:%llx:%llx:%llx:",s.at,s.reads,s.field_a8,s.field_b8,s.field90,s.indirect);hex(f,s.header,sizeof(s.header));std::fputc(':',f);hex(f,s.a8_header,sizeof(s.a8_header));std::fputc(':',f);hex(f,s.b8_header,sizeof(s.b8_header));std::fputc(':',f);hex(f,s.field90_header,sizeof(s.field90_header));std::fputc(':',f);hex(f,s.indirect_header,sizeof(s.indirect_header));std::fputc(';',f);}
    std::fputs("\r\n",f);}std::fclose(f);
  }
 }
 ReleaseSRWLockExclusive(&rows_lock);
}
DWORD WINAPI worker(void*){
 wchar_t path[MAX_PATH]{};GetModuleFileNameW(nullptr,path,MAX_PATH);wchar_t* name=wcsrchr(path,L'\\');if(!name||_wcsicmp(name+1,L"CrimsonDesert.exe"))return 0;
 GetModuleFileNameW(self,directory,MAX_PATH);wchar_t* slash=wcsrchr(directory,L'\\');if(!slash)return 0;slash[1]=0;
 log("Neutral Runtime Probe 0.2. ABI tests pass offline; live binding is unverified. Avatar deformation, sliders and runtime physics are NOT installed by this probe.");log("Press F10 once with game focused to observe up to 64 samples over 20 seconds. No hook is installed until the hotkey is pressed.");
 bool was_down=false,was_capturing=false;
 for(;;){DWORD pid{};GetWindowThreadProcessId(GetForegroundWindow(),&pid);bool down=pid==GetCurrentProcessId()&&(GetAsyncKeyState(VK_F10)&0x8000);
  if(down&&!was_down){if(capture.load()){capture=false;log("Capture stopped.");}else if(written>=64){log("Capture already complete for this launch.");}else if(hooked||install()){next_sample=0;deadline=GetTickCount64()+20000;capture=true;log("Capture started.");}}
  if(capture.load()&&GetTickCount64()>deadline.load())capture=false;
  if(was_capturing&&!capture.load())log("Capture ended. Samples remain local diagnostics; no actor or mesh binding is established by them alone.");
  was_capturing=capture.load();was_down=down;flush();Sleep(50);
 }
}
extern "C" __declspec(dllexport) unsigned NeutralProbeStatusV1(){return (hooked?1u:0u)|(capture.load()?2u:0u);}
BOOL APIENTRY DllMain(HMODULE module,DWORD reason,LPVOID){if(reason==DLL_PROCESS_ATTACH){self=module;DisableThreadLibraryCalls(module);if(HANDLE thread=CreateThread(nullptr,0,worker,nullptr,0,nullptr))CloseHandle(thread);}return TRUE;}
