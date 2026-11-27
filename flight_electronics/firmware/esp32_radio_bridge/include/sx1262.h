// Semtech SX1262 LoRa driver (command interface of the SX1261/2 datasheet, chapter 13).
// Hardware access goes through Sx1262Bus so the same driver runs on the ESP32-S3
// and against the behavioral radio model in the PC simulation.
#pragma once
#include <cstddef>
#include <cstdint>

namespace fe {

class Sx1262Bus {
 public:
  virtual ~Sx1262Bus() = default;
  // One SPI transaction with NSS low for its whole length; waits for BUSY low first.
  virtual void transfer(const uint8_t* tx, uint8_t* rx, size_t len) = 0;
  virtual bool dio1() = 0;
  virtual void reset_pulse() = 0;
  virtual void rf_switch_rx(bool enable) = 0;  // Wio-SX1262 RXEN line
  virtual uint32_t millis() = 0;
};

struct LoraConfig {
  uint32_t frequency_hz = 868100000;
  uint8_t spreading_factor = 7;
  uint32_t bandwidth_hz = 125000;
  uint8_t coding_rate = 5;  // 4/5
  uint16_t preamble = 8;
  int8_t tx_dbm = 22;
  bool tcxo_1v8 = true;  // Wio-SX1262 uses a TCXO powered from DIO3
};

namespace sx {
enum Opcode : uint8_t {
  kSetSleep = 0x84, kSetStandby = 0x80, kSetTx = 0x83, kSetRx = 0x82, kSetRegulatorMode = 0x96,
  kCalibrate = 0x89, kCalibrateImage = 0x98, kSetPaConfig = 0x95, kWriteRegister = 0x0D,
  kWriteBuffer = 0x0E, kReadBuffer = 0x1E, kSetDioIrqParams = 0x08, kGetIrqStatus = 0x12,
  kClearIrqStatus = 0x02, kSetDio2AsRfSwitch = 0x9D, kSetDio3AsTcxo = 0x97, kSetRfFrequency = 0x86,
  kSetPacketType = 0x8A, kSetTxParams = 0x8E, kSetModulationParams = 0x8B, kSetPacketParams = 0x8C,
  kSetBufferBaseAddress = 0x8F, kGetStatus = 0xC0, kGetRxBufferStatus = 0x13, kGetPacketStatus = 0x14,
};
enum Irq : uint16_t {
  kIrqTxDone = 1 << 0, kIrqRxDone = 1 << 1, kIrqHeaderErr = 1 << 5, kIrqCrcErr = 1 << 6,
  kIrqTimeout = 1 << 9,
};
constexpr uint16_t kRegSyncWord = 0x0740;
}  // namespace sx

// LoRa time on air in microseconds (SX1261/2 datasheet section 6.1.4).
uint32_t lora_time_on_air_us(const LoraConfig& cfg, size_t payload_len, bool crc = true,
                             bool explicit_header = true);

class Sx1262 {
 public:
  explicit Sx1262(Sx1262Bus& bus) : bus_(bus) {}
  void begin(const LoraConfig& cfg);
  void start_receive();
  bool transmit(const uint8_t* data, size_t len);  // starts TX; completion via IRQ
  uint16_t irq_status();
  void clear_irq(uint16_t mask);
  // Reads the received packet; returns length (0 on failure).
  size_t read_packet(uint8_t* out, size_t cap, int16_t* rssi_dbm_x10, int8_t* snr_db_x4);
  const LoraConfig& config() const { return cfg_; }

 private:
  void cmd(const uint8_t* tx, size_t len, uint8_t* rx = nullptr);
  void set_packet_params(uint8_t payload_len);
  Sx1262Bus& bus_;
  LoraConfig cfg_;
};

}  // namespace fe
