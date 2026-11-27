// C interface used by the PC simulation (flight_electronics/simulation/radio.py).
// The firmware sources are compiled unchanged; only the bus and the UART are
// replaced by the behavioral SX1262 model and two byte queues.
#include <cstdint>
#include <deque>
#include <vector>

#include "bridge.h"
#include "sx1262_model.h"

#if defined(_WIN32)
#define FE_API extern "C" __declspec(dllexport)
#else
#define FE_API extern "C" __attribute__((visibility("default")))
#endif

namespace {

class QueueUart : public fe::UartPort {
 public:
  void write(const uint8_t* data, size_t len) override { to_companion.insert(to_companion.end(), data, data + len); }
  int read_byte() override {
    if (from_companion.empty()) return -1;
    const int c = from_companion.front();
    from_companion.pop_front();
    return c;
  }
  std::deque<uint8_t> to_companion, from_companion;
};

struct Device {
  uint32_t clock_ms = 0;
  fe::Sx1262Model radio{&clock_ms};
  fe::Sx1262 driver{radio};
  QueueUart uart;
  fe::Bridge bridge{driver, radio, uart};
};

}  // namespace

FE_API void* fe_create(uint32_t frequency_hz, uint8_t sf, int8_t tx_dbm) {
  auto* d = new Device();
  fe::LoraConfig cfg;
  cfg.frequency_hz = frequency_hz;
  cfg.spreading_factor = sf;
  cfg.tx_dbm = tx_dbm;
  d->bridge.begin(cfg);
  return d;
}

FE_API void fe_destroy(void* h) { delete static_cast<Device*>(h); }

// Run the firmware main loop at 1 ms ticks until now_ms.
FE_API void fe_run_until(void* h, uint32_t now_ms) {
  auto* d = static_cast<Device*>(h);
  while (d->clock_ms < now_ms) {
    ++d->clock_ms;
    d->bridge.poll();
  }
}

FE_API void fe_radio_deliver(void* h, const uint8_t* data, uint32_t len, float rssi, float snr, int crc_ok) {
  static_cast<Device*>(h)->radio.deliver(data, len, rssi, snr, crc_ok != 0);
}

FE_API uint32_t fe_uart_read(void* h, uint8_t* out, uint32_t cap) {
  auto& q = static_cast<Device*>(h)->uart.to_companion;
  uint32_t n = 0;
  while (n < cap && !q.empty()) { out[n++] = q.front(); q.pop_front(); }
  return n;
}

FE_API void fe_uart_write(void* h, const uint8_t* data, uint32_t len) {
  auto& q = static_cast<Device*>(h)->uart.from_companion;
  q.insert(q.end(), data, data + len);
}

FE_API int fe_radio_mode(void* h) { return static_cast<Device*>(h)->radio.mode(); }

FE_API uint32_t fe_radio_take_tx(void* h, uint8_t* out, uint32_t cap) {
  std::vector<uint8_t> packet;
  if (!static_cast<Device*>(h)->radio.take_transmitted(&packet)) return 0;
  uint32_t n = 0;
  for (; n < cap && n < packet.size(); ++n) out[n] = packet[n];
  return n;
}

FE_API void fe_counters(void* h, uint32_t* out5) {
  const auto& c = static_cast<Device*>(h)->bridge.counters();
  out5[0] = c.rx_ok; out5[1] = c.rx_bad; out5[2] = c.tx_done; out5[3] = c.reinit; out5[4] = c.frames_from_companion;
}

FE_API uint32_t fe_time_on_air_us(uint8_t sf, uint32_t bw, uint8_t cr, uint16_t preamble, uint32_t len) {
  fe::LoraConfig cfg;
  cfg.spreading_factor = sf; cfg.bandwidth_hz = bw; cfg.coding_rate = cr; cfg.preamble = preamble;
  return fe::lora_time_on_air_us(cfg, len);
}

FE_API uint32_t fe_radio_frequency(void* h) { return static_cast<Device*>(h)->radio.frequency_hz(); }
FE_API int fe_radio_power(void* h) { return static_cast<Device*>(h)->radio.tx_power_dbm(); }
