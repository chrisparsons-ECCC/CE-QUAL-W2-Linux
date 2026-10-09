/* Authorized isolated Linux experiment: change invalid masks only.
 * No model arithmetic, status clearing, signal handler, atexit or restoration.
 * W2_MASK_INVALID=0 is the matched observational control; =1 is candidate.
 */
#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <xmmintrin.h>
#if !defined(__x86_64__)
#error Requires the verified x86-64 execution ABI
#endif
#ifndef W2_MASK_INVALID
#error Explicit experiment mode required
#endif
#if W2_MASK_INVALID != 0 && W2_MASK_INVALID != 1
#error Invalid experiment mode
#endif

typedef struct { _Alignas(16) unsigned char b[512]; } fp_image;
static FILE *receipt;
static fp_image intended;
static int begun;

static void snap(fp_image *s) {
    memset(s->b,0,sizeof s->b);
    __asm__ volatile("fxsave64 %0" : "=m"(*s) : : "memory");
}
static uint16_t u16(const unsigned char *p) { return (uint16_t)((unsigned)p[0]|((unsigned)p[1]<<8)); }
static uint32_t u32(const unsigned char *p) { return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24); }
#if W2_MASK_INVALID
static void put16(unsigned char *p,uint16_t x) {p[0]=(unsigned char)x;p[1]=(unsigned char)(x>>8);}
static void put32(unsigned char *p,uint32_t x) {unsigned i;for(i=0;i<4;i++)p[i]=(unsigned char)(x>>(8*i));}
#endif
/* Compare every bit in architectural control/status/tag words. XMM payloads
 * and last-instruction/data addresses are not caller-preserved FP controls. */
static int same(const fp_image *a,const fp_image *b) {
    return u16(a->b)==u16(b->b) && u16(a->b+2)==u16(b->b+2) && a->b[4]==b->b[4]
        && u32(a->b+24)==u32(b->b+24) && u32(a->b+28)==u32(b->b+28);
}
static int controls_same(const fp_image *a,const fp_image *b) {
    return u16(a->b)==u16(b->b) && (u32(a->b+24)&UINT32_C(0xffffffc0))==(u32(b->b+24)&UINT32_C(0xffffffc0))
        && u32(a->b+28)==u32(b->b+28);
}
static int emit(const char *label,const fp_image *s) {
    unsigned i;
    if(fprintf(receipt,"%s fcw=%04x fsw=%04x ftw=%02x mxcsr=%08x mxcsr_mask=%08x raw32=",
       label,(unsigned)u16(s->b),(unsigned)u16(s->b+2),(unsigned)s->b[4],
       (unsigned)u32(s->b+24),(unsigned)u32(s->b+28))<0)return 0;
    for(i=0;i<32;i++)if(fprintf(receipt,"%02x",(unsigned)s->b[i])<0)return 0;
    return fputc('\n',receipt)!=EOF;
}
static int fail(const char *why) {
    if(receipt) { (void)fprintf(receipt,"FAIL %s\n",why);(void)fflush(receipt); }
    return 86; /* No restoration: caller ends this diagnostic process. */
}

int w2_mask_begin(void) {
    fp_image entry,before,after,guard;
    const char *path;
    int fd;
    snap(&entry);
    if(begun)return fail("DUPLICATE_BEGIN");
    path=getenv("W2_INVALID_MASK_LOG");
    if(!path || !*path)return fail("MISSING_RECEIPT_PATH");
    fd=open(path,O_WRONLY|O_CREAT|O_EXCL,0600);
    if(fd<0)return fail("RECEIPT_OPEN_FAILED");
    receipt=fdopen(fd,"wb");
    if(!receipt){close(fd);return 86;}
    snap(&before);
    if(!same(&entry,&before))return fail("OPEN_CHANGED_FP_CONTROL_OR_STATUS");
    /* FLDCW is a waiting instruction. Reject preexisting unmasked x87
     * exceptions; never clear status or transiently mask unrelated errors. */
    if((u16(before.b+2)&(uint16_t)~u16(before.b)&UINT16_C(0x003f))!=0)
        return fail("PENDING_UNMASKED_X87_EXCEPTION");
    intended=before;
#if W2_MASK_INVALID
    {
        uint16_t cw=(uint16_t)(u16(before.b)|UINT16_C(1));
        uint32_t mx=u32(before.b+24)|UINT32_C(128);
        __asm__ volatile("fldcw %0" : : "m"(cw) : "memory");
        _mm_setcsr(mx);
        put16(intended.b,cw);put32(intended.b+24,mx);
    }
#endif
    snap(&after);
    if(!same(&after,&intended))return fail("UNEXPECTED_FP_CHANGE_AT_BEGIN");
    if(fprintf(receipt,"W2_INVALID_MASK_DIAGNOSTIC 1 candidate=%d\n",W2_MASK_INVALID)<0
       || !emit("BEGIN_ENTRY",&entry) || !emit("BEGIN_BEFORE",&before) || !emit("BEGIN_AFTER",&after)
       || fflush(receipt)!=0)return fail("BEGIN_WRITE_FAILED");
    snap(&guard);
    if(!same(&after,&guard))return fail("BEGIN_LOG_CHANGED_FP_CONTROL_OR_STATUS");
    if(!emit("BEGIN_LOG_AFTER",&guard) || fputs("BEGIN_GUARD_PASS\n",receipt)==EOF || fflush(receipt)!=0)return fail("BEGIN_GUARD_WRITE_FAILED");
    snap(&guard);
    if(!same(&after,&guard))return fail("BEGIN_FINAL_WRITE_CHANGED_FP_CONTROL_OR_STATUS");
    begun=1;
    return 0;
}

int w2_mask_end(void) {
    fp_image before,after;
    FILE *closing;
    int rc;
    snap(&before);
    if(!begun || !receipt)return fail("END_WITHOUT_BEGIN");
    if(!controls_same(&before,&intended))return fail("MODEL_CHANGED_FP_CONTROLS");
    if(!emit("END_BEFORE",&before) || fflush(receipt)!=0)return fail("END_WRITE_FAILED");
    snap(&after);
    if(!same(&before,&after))return fail("END_LOG_CHANGED_FP_CONTROL_OR_STATUS");
    if(!emit("END_LOG_AFTER",&after) || fputs("END_PRE_CLOSE_GUARD_PASS\n",receipt)==EOF || fflush(receipt)!=0)return fail("END_GUARD_WRITE_FAILED");
    closing=receipt;receipt=NULL;rc=fclose(closing);
    snap(&after);
    if(rc!=0 || !same(&before,&after))return 86;
    begun=0;
    return 0;
}
