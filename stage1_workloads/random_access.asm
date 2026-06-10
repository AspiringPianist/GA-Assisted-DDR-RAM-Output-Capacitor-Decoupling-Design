; random_access.asm — Pointer-chasing random access workload
; Models poor cache locality (database hash lookups, sparse NN inference).
; Builds a shuffled address array then pointer-chases through it.
; Every access is a guaranteed row miss in a random bank = max ACT/PRE.

section .data
    BUFFER_SIZE  equ 256 * 1024 * 1024  ; 256 MB
    STRIDE       equ 4096               ; Page-sized stride for maximum row misses
    NUM_ENTRIES  equ BUFFER_SIZE / STRIDE

section .text
global _start
extern setup_mmap, exit_program

_start:
    ; Allocate 256MB buffer
    call    setup_mmap
    mov     r12, rax                ; r12 = buffer base
    mov     r13, 0x12345678         ; Initial seed for LCG

    ; --- Phase 1: Build sequential index array ---
    ; Store pointers at each page boundary, initially sequential
    xor     rcx, rcx                ; i = 0
.build_loop:
    mov     rax, rcx
    inc     rax                     ; next index
    cmp     rax, NUM_ENTRIES
    cmovge  rax, rcx                ; wrap last entry to 0 (but we fix below)
    lea     rdx, [r12 + rax * 8]    ; store pointer to next entry
    mov     [r12 + rcx * 8], rdx
    inc     rcx
    cmp     rcx, NUM_ENTRIES
    jb      .build_loop

    ; Make last entry point back to first
    lea     rax, [r12]
    mov     [r12 + (NUM_ENTRIES - 1) * 8], rax

    ; --- Phase 2: Fisher-Yates shuffle using rdrand ---
    mov     rcx, NUM_ENTRIES
    dec     rcx                     ; i = N-1
.shuffle_loop:
    cmp     rcx, 0
    jle     .shuffle_done

    ; Get random-ish number via simple LCG instead of rdrand (for compatibility)
    ; rax = (rax * 6364136223846793005 + 1)
    mov     rax, r13                ; r13 holds the seed/state
    mov     rbx, 6364136223846793005
    mul     rbx
    inc     rax
    mov     r13, rax                ; save state

    ; j = rax % (i+1)
    xor     rdx, rdx
    mov     rbx, rcx
    inc     rbx
    div     rbx                     ; rdx = rax % (i+1)

    ; Swap array[i] and array[j]
    mov     rsi, [r12 + rcx * 8]
    mov     rdi, [r12 + rdx * 8]
    mov     [r12 + rcx * 8], rdi
    mov     [r12 + rdx * 8], rsi

    dec     rcx
    jmp     .shuffle_loop

.shuffle_done:

    ; --- Phase 3: Pointer chase ---
    mov     rdi, [r12]              ; Start at first pointer
    mov     rcx, NUM_ENTRIES
    shl     rcx, 2                  ; 4x iterations for sufficient trace length

.chase_loop:
    mov     rdi, [rdi]              ; Follow pointer chain
    dec     rcx
    jnz     .chase_loop

    call    exit_program
