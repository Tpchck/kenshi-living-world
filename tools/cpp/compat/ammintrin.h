/* KMM compat: ammintrin.h is missing after KB2519277 (VC++ 2010 SP1 compilers for SDK 7.1).
   Minimal SSE4a declarations; XOP/FMA4 intrinsics are not used by KMM. */
#pragma once
#ifndef _INCLUDED_AMM
#define _INCLUDED_AMM
#include <emmintrin.h>
#ifdef __cplusplus
extern "C" {
#endif
__m128i _mm_extracti_si64(__m128i, int, int);
__m128i _mm_extract_si64(__m128i, __m128i);
__m128i _mm_inserti_si64(__m128i, __m128i, int, int);
__m128i _mm_insert_si64(__m128i, __m128i);
void _mm_stream_sd(double *, __m128d);
void _mm_stream_ss(float *, __m128);
#ifdef __cplusplus
}
#endif
#endif
