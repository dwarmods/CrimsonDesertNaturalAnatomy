option casemap:none
EXTERN gProbeOriginal:QWORD
EXTERN ProbeCapture:PROC
IFDEF PROBE_ABI_TEST
EXTERN ProbeTestReceive:PROC
ENDIF
.code
SAVE_CONTEXT MACRO
 pushfq
 sub rsp,1b0h
 mov [rsp+20h],rax
 mov [rsp+28h],rcx
 mov [rsp+30h],rdx
 mov [rsp+38h],rbx
 lea rax,[rsp+1b8h]
 mov [rsp+40h],rax
 mov [rsp+48h],rbp
 mov [rsp+50h],rsi
 mov [rsp+58h],rdi
 mov [rsp+60h],r8
 mov [rsp+68h],r9
 mov [rsp+70h],r10
 mov [rsp+78h],r11
 mov [rsp+80h],r12
 mov [rsp+88h],r13
 mov [rsp+90h],r14
 mov [rsp+98h],r15
 movdqu [rsp+0a0h],xmm0
 movdqu [rsp+0b0h],xmm1
 movdqu [rsp+0c0h],xmm2
 movdqu [rsp+0d0h],xmm3
 movdqu [rsp+0e0h],xmm4
 movdqu [rsp+0f0h],xmm5
 movdqu [rsp+100h],xmm6
 movdqu [rsp+110h],xmm7
 movdqu [rsp+120h],xmm8
 movdqu [rsp+130h],xmm9
 movdqu [rsp+140h],xmm10
 movdqu [rsp+150h],xmm11
 movdqu [rsp+160h],xmm12
 movdqu [rsp+170h],xmm13
 movdqu [rsp+180h],xmm14
 movdqu [rsp+190h],xmm15
 stmxcsr [rsp+1a0h]
 fnstcw [rsp+1a4h]
ENDM
RESTORE_CONTEXT MACRO
 ldmxcsr [rsp+1a0h]
 fldcw [rsp+1a4h]
 movdqu xmm0,[rsp+0a0h]
 movdqu xmm1,[rsp+0b0h]
 movdqu xmm2,[rsp+0c0h]
 movdqu xmm3,[rsp+0d0h]
 movdqu xmm4,[rsp+0e0h]
 movdqu xmm5,[rsp+0f0h]
 movdqu xmm6,[rsp+100h]
 movdqu xmm7,[rsp+110h]
 movdqu xmm8,[rsp+120h]
 movdqu xmm9,[rsp+130h]
 movdqu xmm10,[rsp+140h]
 movdqu xmm11,[rsp+150h]
 movdqu xmm12,[rsp+160h]
 movdqu xmm13,[rsp+170h]
 movdqu xmm14,[rsp+180h]
 movdqu xmm15,[rsp+190h]
 mov rax,[rsp+20h]
 mov rcx,[rsp+28h]
 mov rdx,[rsp+30h]
 mov rbx,[rsp+38h]
 mov rbp,[rsp+48h]
 mov rsi,[rsp+50h]
 mov rdi,[rsp+58h]
 mov r8,[rsp+60h]
 mov r9,[rsp+68h]
 mov r10,[rsp+70h]
 mov r11,[rsp+78h]
 mov r12,[rsp+80h]
 mov r13,[rsp+88h]
 mov r14,[rsp+90h]
 mov r15,[rsp+98h]
 add rsp,1b0h
 popfq
ENDM
ProbeEntry PROC
 SAVE_CONTEXT
 lea rcx,[rsp+20h]
 call ProbeCapture
 RESTORE_CONTEXT
 jmp QWORD PTR [gProbeOriginal]
ProbeEntry ENDP
IFDEF PROBE_ABI_TEST
ProbeTestOriginal PROC
 SAVE_CONTEXT
 lea rcx,[rsp+20h]
 call ProbeTestReceive
 RESTORE_CONTEXT
 ret
ProbeTestOriginal ENDP
ENDIF
END
