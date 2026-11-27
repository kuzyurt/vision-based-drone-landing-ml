// Radio bridge application: receives boat beacons on LoRa and forwards them to the
// companion computer over UART; sends the drone's status packet to the boat when asked.
#pragma once
#include <cstddef>
#include <cstdint>

#include "protocol.h"
#include "sx1262.h"

namespace fe {

class UartPort {
 public:
  virtual ~UartPort() = default;
  virtual void write(const uint8_t* data, size_t len) = 0;
  virtual int read_byte() = 0;  // -1 when empty
};

enum RadioMode : uint8_t { kModeStandby = 1, kModeRx = 2, kModeTx = 3 };

struct BridgeCounters {
  uint32_t rx_ok = 0, rx_bad = 0, tx_done = 0, reinit = 0, frames_from_companion = 0;
};

class Bridge {
 public:
  Bridge(Sx1262& radio, Sx1262Bus& bus, UartPort& uart) : radio_(radio), bus_(bus), uart_(uart) {}
  void begin(const LoraConfig& cfg);
  // Call often (every 1 ms or on DIO1 interrupt). Never blocks.
  void poll();
  RadioMode mode() const { return mode_; }
  const BridgeCounters& counters() const { return counters_; }

  static constexpr uint32_t kHeartbeatMs = 1000;
  static constexpr uint32_t kSilentReinitMs = 10000;

 private:
  void handle_irq();
  void handle_companion();
  void send_frame(uint8_t type, const uint8_t* payload, size_t len);
  void heartbeat(uint32_t now);

  Sx1262& radio_;
  Sx1262Bus& bus_;
  UartPort& uart_;
  FrameParser parser_;
  BridgeCounters counters_;
  RadioMode mode_ = kModeStandby;
  LoraConfig cfg_;
  uint32_t last_heartbeat_ = 0;
  uint32_t last_radio_activity_ = 0;
  uint8_t pending_status_[32] = {};
  size_t pending_len_ = 0;
  uint16_t status_sequence_ = 0;
};

}  // namespace fe
