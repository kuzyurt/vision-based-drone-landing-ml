#pragma once
#include <cstdint>
int tw_sim_receive(uint8_t *bytes, int capacity);
void tw_sim_send(const uint8_t *bytes, int length);
