// Behavioral model of the SX1262 seen through its SPI command interface.
// It decodes the same opcodes the real chip accepts, keeps the chip state
// (standby / RX / TX), the data buffer and the IRQ register, and finishes a
// transmission after the LoRa time on air. Received packets are injected by
// the simulation with their RSSI and SNR.
#pragma once
#include <cstdint>
#include <cstring>
#include <deque>
#include <vector>

#include "sx1262.h"

namespace fe {

class Sx1262Model : public Sx1262Bus {
 public:
  explicit Sx1262Model(const uint32_t* clock_ms) : clock_(clock_ms) {}

  // Sx1262Bus
  void transfer(const uint8_t* tx, uint8_t* rx, size_t len) override;
  bool dio1() override { advance(); return (irq_ & irq_mask_dio1_) != 0; }
  void reset_pulse() override;
  void rf_switch_rx(bool enable) override { rxen_ = enable; }
  uint32_t millis() override { return *clock_; }

  // Simulation side
  void deliver(const uint8_t* data, size_t len, float rssi_dbm, float snr_db, bool crc_ok);
  void advance();
  uint8_t mode() const { return mode_; }  // 0 sleep, 1 standby, 2 rx, 3 tx
  bool take_transmitted(std::vector<uint8_t>* out);
  uint32_t frequency_hz() const { return uint32_t((uint64_t(frf_) * 32000000ULL) >> 25); }
  uint8_t spreading_factor() const { return sf_; }
  int tx_power_dbm() const { return power_; }
  bool configured_lora() const { return packet_type_ == 1; }
  uint32_t commands() const { return commands_; }

 private:
  const uint32_t* clock_;
  uint8_t mode_ = 1;
  uint8_t packet_type_ = 0;
  uint32_t frf_ = 0;
  uint8_t sf_ = 7, bw_code_ = 4, cr_ = 1;
  uint16_t preamble_ = 8;
  uint8_t payload_len_ = 255;
  int power_ = 0;
  uint16_t irq_ = 0, irq_mask_dio1_ = 0;
  uint8_t buffer_[256] = {};
  uint8_t rx_len_ = 0;
  uint8_t rssi_raw_ = 0;
  int8_t snr_raw_ = 0;
  bool rxen_ = false;
  uint32_t tx_end_ms_ = 0;
  std::vector<uint8_t> tx_payload_;
  std::deque<std::vector<uint8_t>> transmitted_;
  uint32_t commands_ = 0;
};

}  // namespace fe
