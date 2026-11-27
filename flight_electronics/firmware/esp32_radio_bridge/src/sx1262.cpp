#include "sx1262.h"

#include <cmath>
#include <cstring>

namespace fe {

uint32_t lora_time_on_air_us(const LoraConfig& c, size_t pl, bool crc, bool explicit_header) {
  const double tsym = std::ldexp(1.0, c.spreading_factor) / static_cast<double>(c.bandwidth_hz);
  const int de = (c.spreading_factor >= 11 && c.bandwidth_hz <= 125000) ? 1 : 0;
  const int ih = explicit_header ? 0 : 1;
  const int cr = c.coding_rate - 4;  // 4/5 -> 1
  const double num = 8.0 * pl - 4.0 * c.spreading_factor + 28 + 16 * (crc ? 1 : 0) - 20 * ih;
  const double den = 4.0 * (c.spreading_factor - 2 * de);
  const double payload_symbols = 8 + std::fmax(std::ceil(num / den) * (cr + 4), 0.0);
  const double t = (c.preamble + 4.25 + payload_symbols) * tsym;
  return static_cast<uint32_t>(std::lround(t * 1e6));
}

static uint8_t bw_code(uint32_t bw) {
  switch (bw) {
    case 62500: return 0x03;
    case 125000: return 0x04;
    case 250000: return 0x05;
    case 500000: return 0x06;
    default: return 0x04;
  }
}

void Sx1262::cmd(const uint8_t* tx, size_t len, uint8_t* rx) {
  uint8_t scratch[300];
  bus_.transfer(tx, rx ? rx : scratch, len);
}

void Sx1262::begin(const LoraConfig& cfg) {
  cfg_ = cfg;
  bus_.reset_pulse();
  const uint8_t standby[] = {sx::kSetStandby, 0x00};  // STDBY_RC
  cmd(standby, sizeof standby);
  if (cfg.tcxo_1v8) {
    const uint8_t tcxo[] = {sx::kSetDio3AsTcxo, 0x02, 0x00, 0x01, 0x40};  // 1.8 V, 5 ms
    cmd(tcxo, sizeof tcxo);
  }
  const uint8_t calibrate[] = {sx::kCalibrate, 0x7F};
  cmd(calibrate, sizeof calibrate);
  const uint8_t regulator[] = {sx::kSetRegulatorMode, 0x01};  // DC-DC
  cmd(regulator, sizeof regulator);
  const uint8_t rfswitch[] = {sx::kSetDio2AsRfSwitch, 0x01};
  cmd(rfswitch, sizeof rfswitch);
  const uint8_t packet_type[] = {sx::kSetPacketType, 0x01};  // LoRa
  cmd(packet_type, sizeof packet_type);
  const uint8_t image[] = {sx::kCalibrateImage, 0xD7, 0xDB};  // 863-870 MHz band
  cmd(image, sizeof image);
  const uint32_t frf = static_cast<uint32_t>((static_cast<uint64_t>(cfg.frequency_hz) << 25) / 32000000ULL);
  const uint8_t freq[] = {sx::kSetRfFrequency, uint8_t(frf >> 24), uint8_t(frf >> 16), uint8_t(frf >> 8),
                          uint8_t(frf)};
  cmd(freq, sizeof freq);
  const uint8_t pa[] = {sx::kSetPaConfig, 0x04, 0x07, 0x00, 0x01};  // +22 dBm table for SX1262
  cmd(pa, sizeof pa);
  const uint8_t txp[] = {sx::kSetTxParams, uint8_t(cfg.tx_dbm), 0x04};  // 200 us ramp
  cmd(txp, sizeof txp);
  const uint8_t base[] = {sx::kSetBufferBaseAddress, 0x00, 0x00};
  cmd(base, sizeof base);
  const uint8_t mod[] = {sx::kSetModulationParams, cfg.spreading_factor, bw_code(cfg.bandwidth_hz),
                         uint8_t(cfg.coding_rate - 4), 0x00};
  cmd(mod, sizeof mod);
  set_packet_params(255);
  const uint8_t sync[] = {sx::kWriteRegister, sx::kRegSyncWord >> 8, sx::kRegSyncWord & 0xFF, 0x14, 0x24};
  cmd(sync, sizeof sync);  // private network sync word
  const uint16_t mask = sx::kIrqTxDone | sx::kIrqRxDone | sx::kIrqCrcErr | sx::kIrqHeaderErr | sx::kIrqTimeout;
  const uint8_t irq[] = {sx::kSetDioIrqParams, uint8_t(mask >> 8), uint8_t(mask), uint8_t(mask >> 8),
                         uint8_t(mask), 0, 0, 0, 0};
  cmd(irq, sizeof irq);
}

void Sx1262::set_packet_params(uint8_t payload_len) {
  const uint8_t p[] = {sx::kSetPacketParams, uint8_t(cfg_.preamble >> 8), uint8_t(cfg_.preamble),
                       0x00 /* explicit header */, payload_len, 0x01 /* CRC on */, 0x00 /* IQ standard */};
  cmd(p, sizeof p);
}

void Sx1262::start_receive() {
  set_packet_params(255);
  bus_.rf_switch_rx(true);
  const uint8_t rx[] = {sx::kSetRx, 0xFF, 0xFF, 0xFF};  // continuous
  cmd(rx, sizeof rx);
}

bool Sx1262::transmit(const uint8_t* data, size_t len) {
  if (len == 0 || len > 255) return false;
  const uint8_t standby[] = {sx::kSetStandby, 0x00};
  cmd(standby, sizeof standby);
  uint8_t buffer[258] = {sx::kWriteBuffer, 0x00};
  std::memcpy(buffer + 2, data, len);
  cmd(buffer, len + 2);
  set_packet_params(static_cast<uint8_t>(len));
  bus_.rf_switch_rx(false);
  const uint8_t tx[] = {sx::kSetTx, 0x00, 0x00, 0x00};  // no timeout
  cmd(tx, sizeof tx);
  return true;
}

uint16_t Sx1262::irq_status() {
  const uint8_t tx[4] = {sx::kGetIrqStatus, 0, 0, 0};
  uint8_t rx[4] = {};
  cmd(tx, 4, rx);
  return static_cast<uint16_t>((rx[2] << 8) | rx[3]);
}

void Sx1262::clear_irq(uint16_t mask) {
  const uint8_t tx[] = {sx::kClearIrqStatus, uint8_t(mask >> 8), uint8_t(mask)};
  cmd(tx, sizeof tx);
}

size_t Sx1262::read_packet(uint8_t* out, size_t cap, int16_t* rssi, int8_t* snr) {
  const uint8_t status_cmd[4] = {sx::kGetRxBufferStatus, 0, 0, 0};
  uint8_t status[4] = {};
  cmd(status_cmd, 4, status);
  const size_t len = status[2];
  const uint8_t start = status[3];
  if (len == 0 || len > cap) return 0;
  uint8_t tx[260] = {sx::kReadBuffer, start, 0};
  uint8_t rx[260] = {};
  cmd(tx, len + 3, rx);
  std::memcpy(out, rx + 3, len);
  const uint8_t pkt_cmd[5] = {sx::kGetPacketStatus, 0, 0, 0, 0};
  uint8_t pkt[5] = {};
  cmd(pkt_cmd, 5, pkt);
  if (rssi) *rssi = static_cast<int16_t>(-static_cast<int>(pkt[2]) * 5);  // -RssiPkt/2 dBm, x10
  if (snr) *snr = static_cast<int8_t>(pkt[3]);                              // SnrPkt/4 dB, keep x4
  return len;
}

}  // namespace fe
