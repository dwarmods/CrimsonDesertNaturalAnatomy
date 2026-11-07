#include "probe_context.h"
#include "upload_profiles.h"
#include <Windows.h>
#include <MinHook.h>
#include <cstdio>
#include <cstring>
extern "C" void ProbeTestOriginal();
extern "C" {void* gProbeOriginal=nullptr;}
CpuContext before{},after{};
extern "C" void ProbeCapture(const CpuContext* p){before=*p;volatile double stress=3.14159;for(int i=0;i<20;++i)stress=stress*1.01+2.0;}
extern "C" void ProbeTestReceive(const CpuContext* p){after=*p;}
using Eleven=std::uint64_t(*)(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t args[11]{};
std::uint64_t target(std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d,std::uint64_t e,std::uint64_t f,std::uint64_t g,std::uint64_t h,std::uint64_t i,std::uint64_t j,std::uint64_t k){std::uint64_t input[]={a,b,c,d,e,f,g,h,i,j,k};std::memcpy(args,input,sizeof(args));return a^b^c^d^e^f^g^h^i^j^k;}
using Mixed=double(*)(std::uint64_t,double,std::uint64_t,double,std::uint64_t,double);
double mixed(std::uint64_t a,double b,std::uint64_t c,double d,std::uint64_t e,double f){return double(a+c+e)+b+d+f;}
void* chained_original=nullptr;
int prior(){return 0x1234;}
int replacement(){return reinterpret_cast<int(*)()>(chained_original)()+1;}
int main(){
 if(!neutral::upload_profile(0x6aeb7d59,0x13cff000)||!neutral::upload_profile(0x6aed2e85,0x13cc4000)||neutral::upload_profile(0x6aed2e85,0x13cff000)||neutral::upload_profile(0,0)){std::puts("FAIL executable profile guards");return 8;}
 gProbeOriginal=reinterpret_cast<void*>(&ProbeTestOriginal);reinterpret_cast<Eleven>(&ProbeEntry)(1,2,3,4,5,6,7,8,9,10,11);
 if(std::memcmp(before.gpr,after.gpr,sizeof(before.gpr))||std::memcmp(before.xmm,after.xmm,sizeof(before.xmm))||before.flags!=after.flags||before.mxcsr!=after.mxcsr||before.fcw!=after.fcw){std::puts("FAIL register/flags preservation");return 1;}
 gProbeOriginal=reinterpret_cast<void*>(&target);auto value=reinterpret_cast<Eleven>(&ProbeEntry)(1,2,3,4,5,6,7,8,9,10,11);std::uint64_t expected=0;for(int i=0;i<11;++i){if(args[i]!=i+1){std::puts("FAIL stack arguments");return 2;}expected^=i+1;}if(value!=expected){std::puts("FAIL return forwarding");return 3;}
 gProbeOriginal=reinterpret_cast<void*>(&mixed);double number=reinterpret_cast<Mixed>(&ProbeEntry)(1,2.25,3,4.5,5,6.75);if(number!=22.5){std::puts("FAIL SSE/stack mix");return 4;}
 // Relocating a pre-existing short detour must preserve the prior target.
 auto code=static_cast<unsigned char*>(VirtualAlloc(nullptr,4096,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE));if(!code)return 5;
 const unsigned char body[]={0xb8,0x34,0x12,0x00,0x00,0xc3};std::memcpy(code+64,body,sizeof(body));code[0]=0xe9;*reinterpret_cast<int*>(code+1)=59;FlushInstructionCache(GetCurrentProcess(),code,128);
 if(MH_Initialize()!=MH_OK||MH_CreateHook(code,reinterpret_cast<void*>(&replacement),&chained_original)!=MH_OK||MH_EnableHook(code)!=MH_OK)return 6;
 int chained=reinterpret_cast<int(*)()>(code)();MH_DisableHook(code);MH_RemoveHook(code);MH_Uninitialize();VirtualFree(code,0,MEM_RELEASE);
 if(chained!=0x1235){std::puts("FAIL existing detour chain");return 7;}
 std::puts("PASS: GP/XMM registers, flags, MXCSR, x87 control, eleven arguments, mixed SSE/stack arguments, return forwarding and pre-existing jump relocation.");return 0;
}
