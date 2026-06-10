; common.asm — Shared mmap setup and loop scaffolding for DDR4 workloads
; Allocates a 256MB working set via mmap syscall (no libc)
;
; Calling convention: call setup_mmap, returns buffer address in RAX
; Uses: RAX, RDI, RSI, RDX, R10, R8, R9

section .data
    BUFFER_SIZE equ 256 * 1024 * 1024   ; 256 MB

section .text
global setup_mmap

; setup_mmap: allocates BUFFER_SIZE bytes via mmap
; Returns: RAX = pointer to mapped memory (or error code if negative)
setup_mmap:
    ; sys_mmap(addr=NULL, length=BUFFER_SIZE, prot=PROT_READ|PROT_WRITE,
    ;          flags=MAP_PRIVATE|MAP_ANONYMOUS, fd=-1, offset=0)
    mov     rax, 9              ; sys_mmap
    xor     rdi, rdi            ; addr = NULL (kernel chooses)
    mov     rsi, BUFFER_SIZE    ; length
    mov     rdx, 3              ; PROT_READ | PROT_WRITE
    mov     r10, 0x22           ; MAP_PRIVATE | MAP_ANONYMOUS
    mov     r8, -1              ; fd = -1 (no file)
    xor     r9, r9              ; offset = 0
    syscall
    ret

; exit_program: clean exit via sys_exit
global exit_program
exit_program:
    mov     rax, 60             ; sys_exit
    xor     rdi, rdi            ; exit code 0
    syscall
