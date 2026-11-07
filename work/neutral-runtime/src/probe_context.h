#pragma once
#include <cstdint>
#include <cstddef>
struct CpuContext {
 std::uint64_t gpr[16]; // RAX, RCX, RDX, RBX, original RSP, RBP, RSI, RDI, R8..R15
 std::uint8_t xmm[16][16];
 std::uint32_t mxcsr;
 std::uint16_t fcw;
 std::uint8_t reserved[10];
 std::uint64_t flags;
};
static_assert(offsetof(CpuContext,xmm)==0x80);
static_assert(offsetof(CpuContext,mxcsr)==0x180);
static_assert(offsetof(CpuContext,flags)==0x190);
static_assert(sizeof(CpuContext)==0x198);
extern "C" void ProbeEntry();
extern "C" void* gProbeOriginal;
extern "C" void ProbeCapture(const CpuContext*);
