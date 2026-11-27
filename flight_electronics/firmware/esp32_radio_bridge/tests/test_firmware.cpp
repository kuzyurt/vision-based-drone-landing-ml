// Host unit tests for the radio bridge firmware. Build: see build_host.py / Makefile.
#include <cmath>
#include <cstdio>
#include <cstring>
#include <deque>
#include <vector>

#include "bridge.h"
#include "protocol.h"
#include "sx1262.h"
#include "../platform/host/sx1262_model.h"

static int failures = 0;
#define CHECK(cond)                                                     \
  do {                                                                  \
    if (!(cond)) { std::printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #cond); ++failures; } \
  } while (0)

struct Uart : fe::UartPort {
  std::deque<uint8_t> out, in;
  void write(const uint8_t* d, size_t n) override { out.insert(out.end(), d, d + n); }
  int read_byte() override { if (in.empty()) return -1; int c = in.front(); in.pop_front(); return c; }
};

static void test_crc() {
  const uint8_t text[] = "123456789";
  CHECK(fe::crc16_ccitt(text, 9) == 0x29B1);  // CRC-16/CCITT-FALSE check value
}

static void test_time_on_air() {
  fe::LoraConfig c;  // SF7, 125 kHz, 4/5, preamble 8
  // Semtech calculator values: 32 bytes -> 71.94 ms; 10 bytes -> 41.22 ms
  CHECK(fe::lora_time_on_air_us(c, 32) == 71936);
  CHECK(fe::lora_time_on_air_us(c, 10) == 41216);
  c.spreading_factor = 12;  // low data rate optimisation on
  CHECK(std::abs(int(fe::lora_time_on_air_us(c, 10)) - 991232) < 2);
}

static void test_cobs() {
  const uint8_t samples[][6] = {{0, 0, 0, 0, 0, 0}, {1, 2, 0, 3, 4, 5}, {0, 1, 0, 0, 2, 0}};
  for (const auto& s : samples) {
    uint8_t enc[16], dec[16];
    size_t n = fe::cobs_encode(s, 6, enc);
    for (size_t i = 0; i < n; ++i) CHECK(enc[i] != 0);
    CHECK(fe::cobs_decode(enc, n, dec) == 6);
    CHECK(std::memcmp(dec, s, 6) == 0);
  }
  std::vector<uint8_t> big(300, 7);
  std::vector<uint8_t> enc(320), dec(320);
  size_t n = fe::cobs_encode(big.data(), big.size(), enc.data());
  CHECK(fe::cobs_decode(enc.data(), n, dec.data()) == big.size());
}

static void test_beacon_roundtrip() {
  fe::Beacon b{513, 123456, -1234567, 7654321, 45, -120, 300, -5, 3, 25};
  uint8_t raw[32];
  CHECK(fe::beacon_encode(b, raw) == 32);
  fe::Beacon d{};
  CHECK(fe::beacon_decode(raw, 32, &d));
  CHECK(d.sequence == 513 && d.east_cm == -1234567 && d.north_cm == 7654321 && d.ve_cm_s == -120 && d.flags == 3);
  raw[10] ^= 1;
  CHECK(!fe::beacon_decode(raw, 32, &d));
}

static void test_bridge_end_to_end() {
  uint32_t clock = 0;
  fe::Sx1262Model model(&clock);
  fe::Sx1262 driver(model);
  Uart uart;
  fe::Bridge bridge(driver, model, uart);
  fe::LoraConfig cfg;
  bridge.begin(cfg);
  CHECK(model.configured_lora());
  CHECK(model.frequency_hz() > 868099000 && model.frequency_hz() < 868101000);
  CHECK(model.tx_power_dbm() == 22);
  CHECK(model.mode() == 2);

  fe::Beacon b{7, 1000, 100, 200, 30, 10, -20, 0, 1, 30};
  uint8_t raw[32];
  fe::beacon_encode(b, raw);
  clock = 5;
  model.deliver(raw, 32, -97.5f, 6.25f, true);
  bridge.poll();
  fe::FrameParser parser;
  bool got = false;
  while (!uart.out.empty()) {
    uint8_t c = uart.out.front();
    uart.out.pop_front();
    if (parser.push(c) && parser.type() == fe::kFrameBeacon) {
      got = true;
      fe::Beacon d{};
      CHECK(fe::beacon_decode(parser.payload(), 32, &d));
      CHECK(d.sequence == 7 && d.north_cm == 200);
      int16_t rssi = int16_t(parser.payload()[32] | (parser.payload()[33] << 8));
      CHECK(rssi == -975);
      CHECK(int8_t(parser.payload()[34]) == 25);
    }
  }
  CHECK(got);
  CHECK(bridge.counters().rx_ok == 1);

  // Corrupted on air: counted, not forwarded.
  model.deliver(raw, 32, -120.f, -8.f, false);
  bridge.poll();
  CHECK(bridge.counters().rx_bad == 1);

  // Companion asks to send a status packet: it leaves after the time on air.
  uint8_t status[8] = {'D', 'S', 1, 2, 3, 4, 5, 6};
  uint8_t frame[32];
  size_t n = fe::frame_build(fe::kFrameStatus, status, 8, frame, sizeof frame);
  uart.in.insert(uart.in.end(), frame, frame + n);
  bridge.poll();
  CHECK(model.mode() == 3);
  for (int i = 0; i < 40; ++i) { ++clock; bridge.poll(); }
  std::vector<uint8_t> sent;
  CHECK(model.take_transmitted(&sent));
  CHECK(sent.size() == 8 && sent[0] == 'D');
  CHECK(bridge.counters().tx_done == 1);
  CHECK(model.mode() == 2);  // back to receive

  // Silence for longer than the watchdog: the radio is re-initialised.
  for (int i = 0; i < 10100; ++i) { ++clock; bridge.poll(); }
  CHECK(bridge.counters().reinit >= 1);
}

int main() {
  test_crc();
  test_time_on_air();
  test_cobs();
  test_beacon_roundtrip();
  test_bridge_end_to_end();
  if (failures) { std::printf("%d failure(s)\n", failures); return 1; }
  std::printf("firmware host tests passed\n");
  return 0;
}
