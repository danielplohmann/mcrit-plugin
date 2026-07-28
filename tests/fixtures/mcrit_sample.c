#include <stdint.h>

#ifndef MCRIT_VARIANT
#define MCRIT_VARIANT 0
#endif

static uint32_t mcrit_mix(uint32_t value) {
    value ^= 0x9e3779b9u;
    value *= 33u;
#if MCRIT_VARIANT == 1
    value ^= value >> 11;
#elif MCRIT_VARIANT == 2
    value ^= value >> 9;
    value += 0x51u;
#else
    value ^= value >> 13;
#endif
    return value;
}

static uint32_t mcrit_checksum(const uint8_t *data, uint32_t size) {
    uint32_t checksum = 0x12345678u;
    for (uint32_t index = 0; index < size; ++index) {
        checksum = mcrit_mix(checksum ^ data[index]);
    }
    return checksum;
}

static uint32_t mcrit_anchor(uint32_t seed) {
    static const uint8_t input[] = "mcrit-ida-ci-fixture";
    return mcrit_checksum(input, (uint32_t)sizeof(input) - 1u) ^ mcrit_mix(seed);
}

int main(void) {
    return (int)(mcrit_anchor(0x4242u) & 0x7fu);
}
