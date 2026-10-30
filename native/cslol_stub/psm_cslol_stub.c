/*
 * PSM v1.0.5: non-functional compatibility exports for mod-tools mkoverlay.
 *
 * This module does NOT perform injection, hooking, verification avoidance,
 * file redirection, or security checks. The mod-tools binary may require
 * cslol-dll.dll when the Windows loader starts it, even though mkoverlay
 * does not invoke those exports. All callable injection APIs fail closed.
 *
 * Original implementation for Personal Skin Manager; architecture informed
 * by the open-source MIT-licensed Rose cslol_stub design.
 * DO NOT use as a working runoverlay DLL.
 */
#include <stddef.h>

#ifdef _WIN32
#define PSM_EXPORT __declspec(dllexport)
#else
#define PSM_EXPORT
#endif

static const char psm_unsupported[] =
    "Personal Skin Manager: runoverlay is unsupported; use the reviewed LTK host";

PSM_EXPORT const char* cslol_init(void) {
    return psm_unsupported;
}
PSM_EXPORT const char* cslol_set_config(const wchar_t* prefix) {
    (void)prefix;
    return psm_unsupported;
}
PSM_EXPORT const char* cslol_set_flags(unsigned long long flags) {
    (void)flags;
    return psm_unsupported;
}
PSM_EXPORT const char* cslol_set_log_level(unsigned int level) {
    (void)level;
    return psm_unsupported;
}
PSM_EXPORT unsigned int cslol_find(void) {
    return 0;
}
PSM_EXPORT const char* cslol_hook(
    unsigned int thread_id,
    unsigned int timeout,
    unsigned int step
) {
    (void)thread_id;
    (void)timeout;
    (void)step;
    return psm_unsupported;
}
PSM_EXPORT const char* cslol_log_pull(void) {
    return NULL;
}
